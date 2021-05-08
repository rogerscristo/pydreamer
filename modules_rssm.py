from typing import Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributions as D
from torch import Tensor

from modules_tools import *


class RSSMCore(nn.Module):

    def __init__(self, embed_dim=256, action_dim=7, deter_dim=200, stoch_dim=30, hidden_dim=200, global_dim=30):
        super().__init__()
        self._cell = RSSMCell(embed_dim, action_dim, deter_dim, stoch_dim, hidden_dim, global_dim)

    def forward(self,
                embed,       # tensor(N, B, E)
                action,      # tensor(N, B, A)
                reset,       # tensor(N, B)
                in_state: Tuple[Tensor, Tensor],    # tensor(   B, D+S+G)
                glob_state,  # tensor(   B, G)
                ):

        n, b = embed.shape[:2]

        embeds = embed.unbind(0)
        actions = action.unbind(0)
        reset_masks = (~reset.unsqueeze(2)).unbind(0)
        noises = torch.normal(torch.zeros((n, b, self._cell._stoch_dim), device=embed.device),
                              torch.ones((n, b, self._cell._stoch_dim), device=embed.device)).unbind(0)

        priors = []
        posts = []
        states_h = []
        states_z = []
        state = in_state

        for i in range(n):
            post, state = self._cell.forward(embeds[i], actions[i], reset_masks[i], state, glob_state, noises[i])
            posts.append(post)
            states_h.append(state[0])
            states_z.append(state[1])

        posts = torch.stack(posts)
        states_h = torch.stack(states_h)
        states_z = torch.stack(states_z)

        priors = self._cell.batch_prior(states_h)

        features = cat(states_h, states_z)  # TODO: cat3(.., glob_state)

        return (
            priors,                      # tensor(N, B, 2*S)
            posts,                       # tensor(N, B, 2*S)
            features,                    # tensor(N, B, D+S+G)
            (state[0].detach(), state[1].detach()),
        )

    def init_state(self, batch_size):
        return self._cell.init_state(batch_size)


class RSSMCell(nn.Module):

    def __init__(self, embed_dim, action_dim, deter_dim, stoch_dim, hidden_dim, global_dim):
        super().__init__()
        self._stoch_dim = stoch_dim
        self._deter_dim = deter_dim
        self._global_dim = global_dim

        self._z_mlp = nn.Linear(stoch_dim, hidden_dim)
        self._a_mlp = nn.Linear(action_dim, hidden_dim, bias=False)  # No bias, because outputs are added
        # self._g_mlp = nn.Linear(global_dim, hidden_dim, bias=False)  # TODO

        self._gru = nn.GRUCell(hidden_dim, deter_dim)

        self._prior_mlp_h = nn.Linear(deter_dim, hidden_dim)
        # self._prior_mlp_g = nn.Linear(global_dim, hidden_dim, bias=False)  # TODO
        self._prior_mlp = nn.Linear(hidden_dim, 2 * stoch_dim)

        self._post_mlp_h = nn.Linear(deter_dim, hidden_dim)
        # self._post_mlp_g = nn.Linear(global_dim, hidden_dim, bias=False)  # TODO
        self._post_mlp_e = nn.Linear(embed_dim, hidden_dim, bias=False)
        self._post_mlp = nn.Linear(hidden_dim, 2 * stoch_dim)

    def init_state(self, batch_size):
        device = next(self._gru.parameters()).device
        return (
            torch.zeros((batch_size, self._deter_dim), device=device),
            torch.zeros((batch_size, self._stoch_dim), device=device),
        )

    def forward(self,
                embed: Tensor,                    # tensor(B, E)
                action: Tensor,                   # tensor(B, A)
                reset_mask: Tensor,               # tensor(B)
                in_state: Tuple[Tensor, Tensor],  # tensor(B, D+S+G)
                glob_state: Tensor,               # tensor(B, G)
                noise: Tensor,                    # tensor(B, S)
                ):

        in_h, in_z = in_state
        in_h = in_h * reset_mask
        in_z = in_z * reset_mask

        za = F.elu(self._z_mlp(in_z) + self._a_mlp(action))    # (B, H)

        h = self._gru(za, in_h)                                             # (B, D)

        post_in = F.elu(self._post_mlp_h(h) + self._post_mlp_e(embed))
        post = self._post_mlp(post_in)                                    # (B, 2*S)
        sample = rsample(post, noise)                                     # (B, S)

        return (
            post,                         # tensor(B, 2*S)
            (h, sample),                  # tensor(B, D+S+G)
        )

    def batch_prior(self,
                    states_h,     # tensor(N, B, D)
                    ):

        prior_in = F.elu(self._prior_mlp_h(states_h))
        prior = self._prior_mlp(prior_in)               # (N, B, 2*S)
        return prior    # tensor(B, 2*S)

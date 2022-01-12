import os
import threading
import gym
import gym.spaces
import numpy as np
from gym_pybullet_drones.envs.single_agent_rl.BaseSingleAgentAviary import ActionType, ObservationType
from gym_pybullet_drones.envs.single_agent_rl.HoverAviaryDreamer import HoverAviaryDreamer
from gym_pybullet_drones.envs.BaseAviary import BaseAviary

AGGR_PHY_STEPS = 5

class GymPyBulletDrones(gym.Env):
    LOCK = threading.Lock()
    
    # Revisar para gympybulletdrones
    def __init__(self, name, action_repeat=1, size=(64, 64), grayscale=False):
        self._size = size
        with self.LOCK:
            self.env = gym.make(name, #"hover-aviary-dreamer-v0"
                                gui=False,
                                record=False,
                                aggregate_phy_steps=AGGR_PHY_STEPS,
                                obs=ObservationType.IMG,
                                act=ActionType.RPM,
                                vid_width=self._size[0],
                                vid_height=self._size[1],
                                )
        self._action_repeat = action_repeat
        self.grayscale = grayscale

    # Revisar para gympybulletdrones
    @property
    def observation_space(self):
        return gym.spaces.Dict({'image': self.env.observation_space})

    # Revisar para gympybulletdrones
    @property
    def action_space(self):
        return self.env.action_space

    # Revisar para gympybulletdrones
    def step(self, action):
        image, reward, done, info = self.env.step(action)
        if self.grayscale:
            image = image[..., None]
        obs = {'image': image}
        return obs, reward, done, info

    # Revisar para gympybulletdrones
    def reset(self):
        with self.LOCK:
            image: np.ndarray = self.env.reset()  # type: ignore
        if self.grayscale:
            image = image[..., None]
        obs = {'image': image}
        return obs

    # Revisar para gympybulletdrones
    def render(self):
        return self.env.render(mode="human")

# Copyright (c) 2020, RTE (https://www.rte-france.com)
# See AUTHORS.txt
# This Source Code Form is subject to the terms of the Mozilla Public License, version 2.0.
# If a copy of the Mozilla Public License, version 2.0 was not distributed with this file,
# you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of L2RPN Baselines, L2RPN Baselines a repository to host baselines for l2rpn competitions.
import os
import json
import numpy as np


class TrainingParam(object):
    """
    A class to store the training parameters of the models. It was hard coded in the getting_started/notebook 3
    of grid2op and put in this repository instead.

    Attributes
    ----------
    buffer_size: ``int``
        Size of the replay buffer
    minibatch_size: ``int``
        Size of the training minibatch
    update_freq: ``int``
        Frequency at which the model is trained. Model is trained once every `update_freq` steps using `minibatch_size`
        from an experience replay buffer.

    final_epsilon: ``float``
        value for the final epsilon (for the e-greedy)
    initial_epsilon: ``float``
        value for the initial epsilon (for the e-greedy)
    step_for_final_epsilon: ``int``
        number of step at which the final epsilon (for the epsilon greedy exploration) will be reached

    min_observation: ``int``
        number of observations before starting to train the neural nets. Before this number of iterations, the agent
        will simply interact with the environment.

    lr: ``float``
        The initial learning rate
    lr_decay_steps: ``int``
        The learning rate decay step
    lr_decay_rate: ``float``
        The learning rate decay rate

    num_frames: ``int``
        Currently not used

    discount_factor: ``float``
        The discount factor (a high discount factor is in favor of longer episode, a small one not really). This is
        often called "gamma" in some RL paper. It's the gamma in: "RL wants to minize the sum of the dicounted reward,
        which are sum_{t >= t_0} \gamma^{t - t_0} r_t

    tau: ``float``
        Update the target model. Target model is updated according to
        $target_model_weights[i] = self.training_param.tau * model_weights[i] + (1 - self.training_param.tau) * \
                                              target_model_weights[i]$

    min_iter: ``int``
        It is possible in the training schedule to limit the number of time steps an episode can last. This is mainly
        useful at beginning of training, to not get in a state where the grid has been modified so much the agent
        will never get into a state resembling this one ever again). Stopping the episode before this happens can
        help the learning.

    max_iter: ``int``
        Just like "min_iter" but instead of being the minimum number of iteration, it's the maximum.

    max_iter_fun: ``function``
        A function that return the maximum number of steps an episode can count as for the current epoch. For example
        it can be `max_iter_fun = lambda epoch_num : np.sqrt(50 * epoch_num)`

    update_tensorboard_freq: ``int``
        Frequency at which tensorboard is refresh (tensorboard summaries are saved every update_tensorboard_freq
        steps)

    save_model_each: ``int``
        Frequency at which the model is saved (it is saved every "save_model_each" steps)
    """
    _int_attr = ["buffer_size", "minibatch_size", "step_for_final_epsilon",
                  "min_observation", "last_step", "num_frames", "update_freq",
                 "min_iter", "max_iter", "update_tensorboard_freq", "save_model_each"]
    _float_attr = ["final_epsilon", "initial_epsilon", "lr", "lr_decay_steps", "lr_decay_rate",
                    "discount_factor", "tau"]

    def __init__(self,
                 buffer_size=40000,
                 minibatch_size=64,
                 step_for_final_epsilon=100000,  # step at which min_espilon is obtain
                 min_observation=5000,  # 5000
                 final_epsilon=1./(7*288.),  # have on average 1 random action per week of approx 7*288 time steps
                 initial_epsilon=0.4,
                 lr=1e-4,
                 lr_decay_steps=10000,
                 lr_decay_rate=0.999,
                 num_frames=1,
                 discount_factor=0.99,
                 tau=0.1,
                 update_freq=256,
                 min_iter=50,
                 max_iter=8064,  # 1 month
                 update_tensorboard_freq=1000,  # update tensorboard every "update_tensorboard_freq" steps
                 save_model_each=10000  # save the model every "update_tensorboard_freq" steps
                 ):

        self.buffer_size = buffer_size
        self.minibatch_size = minibatch_size
        self.min_observation = min_observation  # 5000
        self.final_epsilon = float(final_epsilon)  # have on average 1 random action per day of approx 288 timesteps at the end (never kill completely the exploration)
        self.initial_epsilon = float(initial_epsilon)
        self.step_for_final_epsilon = float(step_for_final_epsilon)
        self.lr = lr
        self.lr_decay_steps = float(lr_decay_steps)
        self.lr_decay_rate = float(lr_decay_rate)
        self.last_step = 0
        self.num_frames = int(num_frames)
        self.discount_factor = float(discount_factor)
        self.tau = float(tau)
        self.update_freq = update_freq
        self.min_iter = min_iter
        self.max_iter = max_iter

        if self.final_epsilon > 0:
            self._exp_facto = np.log(self.initial_epsilon/self.final_epsilon)
        else:
            # TODO
            self._exp_facto = 1

        self.max_iter_fun = self.default_max_iter_fun

        self.update_tensorboard_freq = update_tensorboard_freq
        self.save_model_each = save_model_each

    def default_max_iter_fun(self, nb_success):
        return int(nb_success * 0.1)  # each time i do 10 episode till the end, i allow the game to continue one more steps

    def tell_step(self, current_step):
        self.last_step = current_step

    def get_next_epsilon(self, current_step):
        self.last_step = current_step
        if current_step > self.step_for_final_epsilon:
            res = self.final_epsilon
        else:
            # exponential decrease
            res = self.initial_epsilon * np.exp(- (current_step / self.step_for_final_epsilon) * self._exp_facto )
        return res

    def to_dict(self):
        res = {}
        for attr_nm in self._int_attr:
            res[attr_nm] = int(getattr(self, attr_nm))
        for attr_nm in self._float_attr:
            res[attr_nm] = float(getattr(self, attr_nm))
        return res

    @staticmethod
    def from_dict(tmp):
        res = TrainingParam()
        for attr_nm in TrainingParam._int_attr:
            if attr_nm in tmp:
                setattr(res, attr_nm, int(tmp[attr_nm]))

        for attr_nm in TrainingParam._float_attr:
            if attr_nm in tmp:
                setattr(res, attr_nm, float(tmp[attr_nm]))

        if res.final_epsilon > 0:
            res._exp_facto = np.log(res.initial_epsilon/res.final_epsilon)
        else:
            # TODO
            res._exp_facto = 1
        return res

    @staticmethod
    def from_json(json_path):
        if not os.path.exists(json_path):
            raise FileNotFoundError("No path are located at \"{}\"".format(json_path))
        with open(json_path, "r") as f:
            dict_ = json.load(f)
        return TrainingParam.from_dict(dict_)

    def save_as_json(self, path, name=None):
        res = self.to_dict()
        if name is None:
            name = "training_parameters.json"
        if not os.path.exists(path):
            raise RuntimeError("Directory \"{}\" not found to save the training parameters".format(path))
        if not os.path.isdir(path):
            raise NotADirectoryError("\"{}\" should be a directory".format(path))
        path_out = os.path.join(path, name)
        with open(path_out, "w", encoding="utf-8") as f:
            json.dump(res, fp=f, indent=4, sort_keys=True)

    def do_train(self):
        return self.last_step % self.update_freq == 0
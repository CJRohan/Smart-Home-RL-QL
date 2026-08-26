"""Basic tabular Q-learning with only Python's standard library."""

import random


class QLearningAgent:
    """Stores one value for each encountered state and valid action."""

    def __init__(self, config, seed=None):
        choices = config["q_learning_parameters"]
        self.learning_rate = choices["learning_rate"]
        self.discount_factor = choices["discount_factor"]
        self.random = random.Random(config["experiment"]["seed"] if seed is None else seed)
        self.q_table = {}

    def value(self, state, action):
        return self.q_table.get((state, action), 0.0)

    def choose_action(self, state, valid_actions, epsilon):
        """Explore randomly, otherwise use the best currently-known valid action."""
        if self.random.random() < epsilon:
            return self.random.choice(valid_actions)

        values = [self.value(state, action) for action in valid_actions]
        best_value = max(values)
        best_actions = [action for action, value in zip(valid_actions, values) if value == best_value]
        return self.random.choice(best_actions)

    def learn(self, state, action, reward, next_state, next_valid_actions, finished):
        """Apply: Q(s,a) = Q(s,a) + alpha * [reward + gamma*max Q(s',a') - Q(s,a)]."""
        old_value = self.value(state, action)
        best_future = 0.0 if finished else max(
            self.value(next_state, next_action) for next_action in next_valid_actions
        )
        target = reward + self.discount_factor * best_future
        self.q_table[(state, action)] = old_value + self.learning_rate * (target - old_value)

"""Small training loop. Kept separate so it is not run for this review package."""

from config_loader import ConfigLoader
from q_learning_agent import QLearningAgent
from scenario_generator import ScenarioGenerator
from smart_home_environment import SmartHomeEnvironment


def train(number_of_days=1000):
    """Generate training days and update a basic Q-table. No files are saved here."""
    config = ConfigLoader().load()
    generator = ScenarioGenerator(config)
    environment = SmartHomeEnvironment(config)
    agent = QLearningAgent(config)
    start_epsilon = config["q_learning_parameters"]["epsilon_start"]
    end_epsilon = config["q_learning_parameters"]["epsilon_end"]

    for day_index, scenario in enumerate(generator.generate_days(number_of_days)):
        epsilon = start_epsilon + (end_epsilon - start_epsilon) * day_index / max(1, number_of_days - 1)
        state = environment.reset(scenario)
        finished = False
        while not finished:
            action = agent.choose_action(state, environment.valid_actions(), epsilon)
            next_state, reward, finished, _ = environment.step(action)
            next_actions = ["do_nothing"] if finished else environment.valid_actions()
            agent.learn(state, action, reward, next_state, next_actions, finished)
            state = next_state
    return agent

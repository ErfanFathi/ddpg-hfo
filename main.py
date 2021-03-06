import numpy as np
import torch
import os

import utils
import DDPG
import random
import gym
import gym_soccer
from torch.utils.tensorboard import SummaryWriter

def evaluation(env, policy):
	state, done = env.reset(), False
	total_reward = 0
	eps = 0
	while eps < 200:
		action = policy.select_action(state)
		next_state, reward, done , _= env.step(suit_action(action))
		state = next_state
		total_reward += reward

		if done:
			state, done = env.reset(), False
			eps += 1
	
	return total_reward/200
		

def suit_action(action):
	ret_act = np.zeros(6)
	ret_act[0] = np.argmax(action[0:3])
	ret_act[1:6] = action[3:8]
	return ret_act

def add_on_policy_mc(transitions):
	r = 0
	dis = 0.99
	for i in range(len(transitions)-1,-1,-1):
		r = transitions[i]["reward"]+dis*r
		transitions[i]["n_step"] = r

if __name__ == "__main__":
	
	# tensor-board
	writer = SummaryWriter()

	seed = 0
	save_model = False
	start_timesteps = 1000
	batch_size = 256

	file_name = "DDPG_" + "HFO_" + str(seed)
	print("---------------------------------------")
	print(f"Policy: DDPG, Env: HFO, Seed: {seed}")
	print("---------------------------------------")

	if not os.path.exists("./results"):
		os.makedirs("./results")

	if save_model and not os.path.exists("./models"):
		os.makedirs("./models")

	torch.manual_seed(seed)
	np.random.seed(seed)
	

	max_a = [1,1,1,100,180,180,100,180]
	min_a = [-1,-1,-1,0,-180,-180,0,-180]
	state_dim = 59
	action_dim = len(max_a)

	policy = DDPG.DDPG(state_dim, action_dim, max_a, min_a)

	replay_buffer = utils.ReplayBuffer(state_dim, action_dim)

	env = gym.make('SoccerScoreGoal-v0')
	state, done = env.reset(), False
	episode_reward = 0
	episode_timesteps = 0
	episode_num = 0
	transitions = []
	high_eval = 0
	timestep = 0
	evaluation_num = 0
	while episode_num<=100000:
		eps_rnd = random.random()
		dec =min(max(0.1,1.0 - float(timestep-start_timesteps)*0.00009),1)
		if eps_rnd<dec or timestep < start_timesteps:
			action = (np.array([random.uniform(-1,+1),random.uniform(-1,+1),random.uniform(-1,+1),
			random.uniform(0,100),random.uniform(-180,+180),
			random.uniform(-180,+180),random.uniform(0,100),random.uniform(-180,+180)]))
		else:
			action =policy.select_action(state)
		next_state, reward, done ,info= env.step(suit_action(action)) 
		done_bool = float(done)

		transitions.append({"state" : state,
							"action" : action,
							"next_state" : next_state,
							"reward" : reward,
							"done" : done_bool
							})

		state = next_state
		episode_reward += reward

		timestep += 1
		episode_timesteps+=1

		if done: 
			add_on_policy_mc(transitions)
			for i in transitions:
				replay_buffer.add(i["state"], i["action"], i["next_state"],
									i["reward"], i["n_step"], i["done"])
			if timestep >= start_timesteps:
				for i in range(int(episode_timesteps/10)):
					policy.train(replay_buffer, batch_size)

			writer.add_scalar("reward/episode", episode_reward, episode_num)
			
			state, done = env.reset(), False
			episode_reward = 0
			transitions = []
			episode_timesteps = 0
			episode_num += 1 

			if (episode_num+1) % 500 == 0 :
				evaluation_num += 1
				current_eval = evaluation(env, policy)
				print('evaluation : ', current_eval)
				writer.add_scalar("current_eval/test_number", current_eval, nt)
				if current_eval > high_eval:
					policy.save('./models/model')
					high_eval = current_eval
					print('saved in ',episode_num)
				state, done = env.reset(), False
		
	writer.flush()
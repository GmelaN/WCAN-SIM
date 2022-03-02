#################################################
##			    How to use BANSIM			   ##
#################################################


## Description

* BANSIM is a discrete-event network simulator for wireless body area networks (WBANs) in standard Python 
  that supports deep reinforcement learning (DRL). BANSIM provides an intuitive and simple DRL development 
  environment with basic packet communication and BAN-specific components, such as human mobility model 
  and on-body channel model.
* Users can easily build a WBAN environment, design a DRL-based protocol, and evaluate its performance. 
  In addition, users can extend BANSIM to other networks by defining a new upper-layer or modifying 
  MAC/PHY components.
* BANSIM is implemented based on SimPy component model. SimPy is a process-based discrete-event simulation 
  framework for Python. The detailed information on SimPy can be found at https://simpy.readthedocs.io/en/latest/. 

## Environment

* Users can run BANSIM in Standard Python environment. Specifically, BANSIM is implemented in the following 
  environment.
* OS: Window 10
* Processor: Intel(R) Core(TM) i7-6700K CPU (x64)
* RAM: 16 GB
* Python IDE: PyCharm
* Project interpreter: Python 3.7

## Prerequisite

* To compile BANSIM, the following packages must be installed in the Python development environment.
* simpy
* numpy
* keras
* tensorflow
* math
* random

## Files

* BANSIM includes the following class files.

# dqn_trainer.py: In this file, DQNTrainer class model is implemented.
 - DQNTrainer model includes DQN components and defines interface methods for DQN training. 
   In this files, users can simply create a neural network using sequential model, or 
   configure a complex neural network using the functional API provided by Keras.
 - For beginners, several sample models are provided: 1) Sequential model, 2) Fully-connected FFNN, 
  3) Linear regression, 4) Multiple inputs model, 5) Recurrence neural network (RNN).

# mobility_model.py: This file provides three types of human mobility models: standing, sitting, and walking.

# trace.py: In this file, performance statistics are collected during the simulation.

# wban_header.py/wban_packet.py: In these files, BanMacHeader/Packet class models are implemented.
 - BanMacHeader/Packet models define the MAC header and MAC frame body specified in the IEEE 802.15.6 standard.

# wban_protocol_stack.py: In this file, UpperLayer/SSCS/MAC/PHY class models are implemented.
 - UpperLayer model is an abstract class and provides interface methods for developing a higher-layer.
 - SSCS model provides a service access point between higher-layers/DQN trainer and MAC.
 - MAC model supports a communication mode: beacon mode with superframes and provides two types of 
   channel-access modes: TDMA and CSMA/CA.
 - PHY model supports narrowband (NB) PHY and is responsible for 1) radio transceiver control, 2) CCA, 
  3) data transmission/reception.

# wireless_model.py: In this file, PropLossModel/PropDelayModel class models are implemented.
 - PropLossModel defines two types of path loss models: 1) friis propagation loss model, 
  2) BAN-specific propagation loss model.
 - PropDelayModel calculates propagation delay based on the propagation speed of light in the vacuum.

# node.py: In this file, users can configure the node specification (e.g., data priority, data rate, and data size)

# wban_test.py: In this file, an example code for configuring a WBAN is presented.

## Usage
* To run BANSIM, users must initialize node/channel models.
* An example code for configuring a WBAN is given in wban_test.py

# Create SimPy environment
* env = simpy.Environment()

# Create a node container
* node = Node(env)

# Create an agent container
* agent = Agent(env)

# Initialize network interface parameters
* agent.set_device_params(param1, param2, param3) # (ban ID, node ID, recipient ID)
* node.set_device_params(param1, param2, param3)

# Register the node ID in the agent for resource allocation
* agent.set_node_list(node ID)

# Create a channel environment
* channel = BanChannel(env)
* prop_loss_model = PropLossModel()
* prop_loss_model.set_frequency(param) # (operating bandwidth)
* prop_delay_model = PropDelayModel()
* channel.set_prop_loss_model(prop_loss_model)
* channel.set_prop_delay_model(prop_delay_model)

# Setting a channel to the network interface
* node.set_channel(channel)
* agent.set_channel(channel)

# Setting a mobility model
* mobility = MobilityModel(param) # (BodyPosition)
* node.m_phy.set_mobility(mobility)

# Make a mobilityModel helper class
* mobility_helper = MobilityHelper(env)
* mobility_helper.add_mobility_list(mobility)

# Generate packet events
* event = env.event()
* event._ok = True
* event.callbacks.append(agent.start)
* event.callback.append(node.generate_data)
* env.schedule(event, priority=0, delay=0)

# Generate mobility events
* event = env.event()
* event._ok = True
* event.callbacks.append(mobility_helper.do_walking)
* env.schedule(event, priority=0, delay=0)

# Set the simulation run time
* run_time = 50000  # seconds

# Print statistical results
event = env.event()
event._ok = True
event.callbacks.append(node.m_mac.show_result)
env.schedule(event, priority=0, delay=200)

# Run simulation
env.run(until=run_time)
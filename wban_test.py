from node import *

 
# Test start
env = simpy.Environment()  # Create the SimPy environment

# Create node containers
n1 = Node(env)
n2 = Node(env)
n3 = Node(env)
n4 = Node(env)
n5 = Node(env)
n6 = Node(env)
n7 = Node(env)
n8 = Node(env)

# Create an agent container
agent = Agent(env)

# Initialize network interface params
agent.set_device_params(0, 10, None)
n1.set_device_params(0, 1, 10)     # (ban id, node id, recipient id)
n2.set_device_params(0, 2, 10)
n3.set_device_params(0, 3, 10)
n4.set_device_params(0, 4, 10)
n5.set_device_params(0, 5, 10)
n6.set_device_params(0, 6, 10)
n7.set_device_params(0, 7, 10)
n8.set_device_params(0, 8, 10)


# Register the node id in the agent for resource allocation
agent.set_node_list(1)
agent.set_node_list(2)
agent.set_node_list(3)
agent.set_node_list(4)
agent.set_node_list(5)
agent.set_node_list(6)
agent.set_node_list(7)
agent.set_node_list(8)

# Create a channel environment
channel = BanChannel(env)      # All nodes share a channel environment
prop_loss_model = PropLossModel()
prop_loss_model.set_frequency(0.915e9)  # We assume the wireless channel operates in 915 Mhz
prop_delay_model = PropDelayModel()
channel.set_prop_loss_model(prop_loss_model)
channel.set_prop_delay_model(prop_delay_model)

# Setting up a channel to the network interfaces
n1.set_channel(channel)
n2.set_channel(channel)
n3.set_channel(channel)
n4.set_channel(channel)
n5.set_channel(channel)
n6.set_channel(channel)
n7.set_channel(channel)
n8.set_channel(channel)

agent.set_channel(channel)

# Create/ setting up mobility models
mob_n1 = MobilityModel(BodyPosition.left_elbow)
mob_n2 = MobilityModel(BodyPosition.left_wrist)
mob_n3 = MobilityModel(BodyPosition.right_elbow)
mob_n4 = MobilityModel(BodyPosition.right_wrist)
mob_n5 = MobilityModel(BodyPosition.left_knee)
mob_n6 = MobilityModel(BodyPosition.left_ankle)
mob_n7 = MobilityModel(BodyPosition.right_knee)
mob_n8 = MobilityModel(BodyPosition.right_ankle)
mob_agent = MobilityModel(BodyPosition.right_lower_torso)

n1.m_phy.set_mobility(mob_n1)
n2.m_phy.set_mobility(mob_n2)
n3.m_phy.set_mobility(mob_n3)
n4.m_phy.set_mobility(mob_n4)
n5.m_phy.set_mobility(mob_n5)
n6.m_phy.set_mobility(mob_n6)
n7.m_phy.set_mobility(mob_n7)
n8.m_phy.set_mobility(mob_n8)
agent.m_phy.set_mobility(mob_agent)

# TODO: Make a mobilityModel helper class
mobility_helper = MobilityHelper(env)
mobility_helper.add_mobility_list(mob_n1)
mobility_helper.add_mobility_list(mob_n2)
mobility_helper.add_mobility_list(mob_n3)
mobility_helper.add_mobility_list(mob_n4)
mobility_helper.add_mobility_list(mob_n5)
mobility_helper.add_mobility_list(mob_n6)
mobility_helper.add_mobility_list(mob_n7)
mobility_helper.add_mobility_list(mob_n8)
mobility_helper.add_mobility_list(mob_agent)

# Generate events (generate packet events)
event = env.event()
event._ok = True
event.callbacks.append(agent.start)
event.callbacks.append(n1.generate_data)
event.callbacks.append(n2.generate_data)
event.callbacks.append(n3.generate_data)
event.callbacks.append(n4.generate_data)
event.callbacks.append(n5.generate_data)
event.callbacks.append(n6.generate_data)
event.callbacks.append(n7.generate_data)
event.callbacks.append(n8.generate_data)
env.schedule(event, priority=0, delay=0)

# Generate events (generate mobility)
event = env.event()
event._ok = True
event.callbacks.append(mobility_helper.do_walking)

env.schedule(event, priority=0, delay=0)

# Set the simulation run time
run_time = 50000  # seconds

# Print statistical results
event = env.event()
event._ok = True
event.callbacks.append(n1.m_mac.show_result)
event.callbacks.append(n2.m_mac.show_result)
event.callbacks.append(n3.m_mac.show_result)
event.callbacks.append(n4.m_mac.show_result)
event.callbacks.append(n5.m_mac.show_result)
event.callbacks.append(n6.m_mac.show_result)
event.callbacks.append(n7.m_mac.show_result)
event.callbacks.append(n8.m_mac.show_result)
env.schedule(event, priority=0, delay=200)

# Run simulation
env.run(until=run_time)
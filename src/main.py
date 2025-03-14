import sims4.commands
import services

@sims4.commands.Command('helloworld', command_type=sims4.commands.CommandType.Live)
def helloworld(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output("This is my first script mod")
    sim_info_manager = services.sim_info_manager()
    active_sim_info = sim_info_manager.get_active_sim_info()
    if active_sim_info is not None:
        output(f"Active Sim: {active_sim_info}")
    else:
        output("No active Sim found")

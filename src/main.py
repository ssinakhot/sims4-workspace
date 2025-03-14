import sims4.commands
import services

@sims4.commands.Command('noai', command_type=sims4.commands.CommandType.Live)
def noai(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output("This is my first script mod")
    sim_info_manager = services.sim_info_manager()
    active_sim_info = sim_info_manager.get_active_sim_info()
    if active_sim_info is not None:
        output(f"Active Sim: {active_sim_info}")
    else:
        output("No active Sim found")

    # Disable autonomy for all Sims
    autonomy_service = services.autonomy_service()
    if autonomy_service is not None:
        autonomy_service.set_all_sims_autonomy_enabled(False)
        output("Autonomy has been disabled for all Sims")
    else:
        output("Failed to disable autonomy")

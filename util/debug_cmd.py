import sims4.commands


@sims4.commands.Command('pycharm.debug', command_type=sims4.commands.CommandType.Live)
def _pycharm_debug(_connection: int = None) -> None:
    """
    This creates an in-game cheat code 'pycharm.debug', when entered it sets up and connects the debugger to PyCharm Pro

    :param _connection: A special number provided automatically by the game
    :return: Nothing
    """

    # Access the cheat console using the access number provided by the game and inform the user what to do
    output = sims4.commands.CheatOutput(_connection)
    output("Debug Initiated")
    output("There are now many red error messages in PyCharm, ignore them, this is normal.")
    output("Please open your PyCharm Pro editor now and click resume...")

    # Initiate the connection, the debugger will pause 2 lines down from here until the user resumes manually
    import pydevd_pycharm
    pydevd_pycharm.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True)

    # Inform the user the debugger is ready and setup
    output("")
    output("The debugger has been successfully setup, your ready to start adding breakpoints and begin debugging")

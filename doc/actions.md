# UI: Actions

```python
# Application
actions.add('application.settings', "Settings", 'F10', None, Application.show_settings_dialog)
actions.add('application.quit', "Quit", 'Ctrl+Q', None, Application.quit_local)
actions.add('application.import', "Import...", 'Ctrl+I', None, Application.show_import_wizard)
actions.add('application.export', "Export...", 'Ctrl+E', None, Application.show_export_wizard)
actions.add('application.about', "About", '', None, Application.show_about)

# BacklogTableView
actions.add('backlogs_table.newBacklog', "New Backlog", 'Ctrl+N', None, BacklogTableView.create_backlog)
actions.add('backlogs_table.renameBacklog', "Rename Backlog", 'Ctrl+R', None, BacklogTableView.rename_selected_backlog)
actions.add('backlogs_table.deleteBacklog', "Delete Backlog", 'F8', None, BacklogTableView.delete_selected_backlog)

# WorkitemTableView
actions.add('workitems_table.newItem', "New Item", 'Ins', None, WorkitemTableView.create_workitem)
actions.add('workitems_table.renameItem', "Rename Item", 'F6', None, WorkitemTableView.rename_selected_workitem)
actions.add('workitems_table.deleteItem', "Delete Item", 'Del', None, WorkitemTableView.delete_selected_workitem)
actions.add('workitems_table.startItem', "Start Item", 'Ctrl+S', 'tool-next', WorkitemTableView.start_selected_workitem)
actions.add('workitems_table.completeItem', "Complete Item", 'Ctrl+P', 'tool-complete', WorkitemTableView.complete_selected_workitem)
actions.add('workitems_table.addPomodoro', "Add Pomodoro", 'Ctrl++', None, WorkitemTableView.add_pomodoro)
actions.add('workitems_table.removePomodoro', "Remove Pomodoro", 'Ctrl+-', None, WorkitemTableView.remove_pomodoro)
actions.add('workitems_table.showCompleted', "Show Completed Items", '', None, WorkitemTableView._toggle_show_completed_workitems, True, True)

# FocusWidget
actions.add('focus.voidPomodoro', "Void Pomodoro", 'Ctrl+V', "tool-void", FocusWidget._void_pomodoro)
actions.add('focus.nextPomodoro', "Next Pomodoro", None, "tool-next", FocusWidget._next_pomodoro)
actions.add('focus.completeItem', "Complete Item", None, "tool-complete", FocusWidget._complete_item)
actions.add('focus.showFilter', "Show Filter", None, "tool-filter", FocusWidget._display_filter)

# MainWindow
actions.add('window.showAll', "Show All", None, "tool-show-all", MainWindow.show_all)
actions.add('window.showFocus', "Show Focus", None, "tool-show-timer-only", MainWindow.show_focus)
actions.add('window.showMainWindow', "Show Main Window", None, "tool-show-timer-only", MainWindow.show_window)
actions.add('window.showBacklogs', "Backlogs", 'Ctrl+B', 'tool-backlogs', MainWindow.show_about)
actions.add('window.showUsers', "Team", 'Ctrl+T', 'tool-teams', MainWindow.toggle_users)
actions.add('window.showSearch', "Search...", 'Ctrl+F', '', MainWindow.show_search)
```

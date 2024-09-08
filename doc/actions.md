# UI: Actions

## Application
- ('application.settings', "Settings", 'F10', None, Application.show_settings_dialog)
- ('application.quit', "Quit", 'Ctrl+Q', None, Application.quit_local)
- ('application.import', "Import...", 'Ctrl+I', None, Application.show_import_wizard)
- ('application.export', "Export...", 'Ctrl+E', None, Application.show_export_wizard)
- ('application.about', "About", '', None, Application.show_about)

## BacklogTableView
- ('backlogs_table.newBacklog', "New Backlog", 'Ctrl+N', None, BacklogTableView.create_backlog)
- ('backlogs_table.renameBacklog', "Rename Backlog", 'Ctrl+R', None, BacklogTableView.rename_selected_backlog)
- ('backlogs_table.deleteBacklog', "Delete Backlog", 'F8', None, BacklogTableView.delete_selected_backlog)
- ('backlogs_table.newBacklogFromIncomplete', "New Backlog From Incomplete", 'Ctrl+M', "tool-add-prefilled", BacklogTableView.create_backlog_from_incomplete)

## WorkitemTableView
- ('workitems_table.newItem', "New Item", 'Ins', None, WorkitemTableView.create_workitem)
- ('workitems_table.renameItem', "Rename Item", 'F6', None, WorkitemTableView.rename_selected_workitem)
- ('workitems_table.deleteItem', "Delete Item", 'Del', None, WorkitemTableView.delete_selected_workitem)
- ('workitems_table.startItem', "Start Item", 'Ctrl+S', 'tool-next', WorkitemTableView.start_selected_workitem)
- ('workitems_table.completeItem', "Complete Item", 'Ctrl+P', 'tool-complete', WorkitemTableView.complete_selected_workitem)
- ('workitems_table.addPomodoro', "Add Pomodoro", 'Ctrl++', None, WorkitemTableView.add_pomodoro)
- ('workitems_table.removePomodoro', "Remove Pomodoro", 'Ctrl+-', None, WorkitemTableView.remove_pomodoro)
- ('workitems_table.showCompleted', "Show Completed Items", '', None, WorkitemTableView._toggle_show_completed_workitems, True, True)

## FocusWidget
- ('focus.voidPomodoro', "Void Pomodoro", 'Ctrl+V', "tool-void", FocusWidget._void_pomodoro)
- ('focus.nextPomodoro', "Next Pomodoro", None, "tool-next", FocusWidget._next_pomodoro)
- ('focus.completeItem', "Complete Item", None, "tool-complete", FocusWidget._complete_item)
- ('focus.showFilter', "Show Filter", None, "tool-filter", FocusWidget._display_filter)

## MainWindow
- ('window.showAll', "Show All", None, "tool-show-all", MainWindow.show_all)
- ('window.showFocus', "Show Focus", None, "tool-show-timer-only", MainWindow.show_focus)
- ('window.showMainWindow', "Show Main Window", None, "tool-show-timer-only", MainWindow.show_window)
- ('window.showBacklogs', "Backlogs", 'Ctrl+B', 'tool-backlogs', MainWindow.show_about)
- ('window.showUsers', "Team", 'Ctrl+T', 'tool-teams', MainWindow.toggle_users)
- ('window.showSearch', "Search...", 'Ctrl+F', '', MainWindow.show_search)

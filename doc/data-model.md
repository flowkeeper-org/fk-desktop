# Data model

Flowkeeper data model is strictly hierarchical:

- Tenant: AbstractDataContainer
  - User: AbstractDataContainer
    - Backlog: AbstractDataContainer
      - Workitem: AbstractDataContainer
        - Pomodoro: AbstractDataItem

`AbstractDataContainer` acts as a `dict<uid, T>`, and `AbstractDataItem` represents a domain object with 
`uid`, `parent`, `create_date` and `last_modified_date`. 

Due to its tree nature, sharing backlogs and workitems should be implemented via symlinks.

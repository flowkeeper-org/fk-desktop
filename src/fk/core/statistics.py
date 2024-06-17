#  Flowkeeper - Pomodoro timer for power users and teams
#  Copyright (c) 2023 Constantine Kulak
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
from fk.core.pomodoro import Pomodoro


def pipeline():
    # 1. Extract typed data points from data<TRoot>, e.g. a generator for Pomodoros, with filters applied
    # 2. A set of functions / getters to get facets / views of those data points <-- series
    # 3. Group generator, with group object being comparable / sortable + __str__
    # 4. Aggregation function

    group_generator = DateGroupGenerator(DateGrouping.Month, Pomodoro.get_last_modified_date)
    group_generator.append(PomodoroExtractor(DateFilter(date_from, date_to)).generate(data))
    finished_aggregator = CountAggregator(Pomodoro.is_finished)
    canceled_aggregator = CountAggregator(Pomodoro.is_canceled)
    ready_aggregator = CountAggregator(Pomodoro.is_startable)
    for g in group_generator.get_groups():
        print(f'X = {g}:')
        print(finished_aggregator.aggregate(g.values()))
        print(canceled_aggregator.aggregate(g.values()))
        print(ready_aggregator.aggregate(g.values()))

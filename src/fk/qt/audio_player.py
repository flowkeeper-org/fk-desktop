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

from PySide6.QtCore import QObject
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QAudio
from PySide6.QtWidgets import QWidget

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import SourceMessagesProcessed
from fk.core.timer import PomodoroTimer


class AudioPlayer(QObject):
    _timer: PomodoroTimer
    _audio_output: QAudioOutput
    _audio_player: QMediaPlayer
    _settings: AbstractSettings

    def __init__(self,
                 parent: QWidget,
                 source_holder: EventSourceHolder,
                 settings: AbstractSettings,
                 timer: PomodoroTimer):
        super().__init__(parent)
        self._timer = timer
        self._settings = settings
        self._reset()
        timer.on("Timer*Complete", self._play_audio)
        timer.on("TimerWorkStart", self._start_ticking)
        source_holder.on(AfterSourceChanged, self._on_source_changed)

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        if self._audio_player.isPlaying():
            self._audio_player.stop()
        source.on(SourceMessagesProcessed, self._on_messages)

    def _reset(self):
        self._audio_output = QAudioOutput()
        self._audio_player = QMediaPlayer(self.parent())
        self._audio_player.setAudioOutput(self._audio_output)

    def _set_volume(self, setting: str):
        volume = float(self._settings.get(setting)) / 100.0
        # This is what all mixers do
        volume = QAudio.convertVolume(volume,
                                      QAudio.VolumeScale.LogarithmicVolumeScale,
                                      QAudio.VolumeScale.LinearVolumeScale)
        self._audio_output.setVolume(volume)
        print(f'Volume is set to {int(volume * 100)}%')

    def _play_audio(self, event: str = None, **kwargs) -> None:
        # Alarm bell
        play_alarm_sound = (self._settings.get('Application.play_alarm_sound') == 'True')
        play_rest_sound = (self._settings.get('Application.play_rest_sound') == 'True')
        if play_alarm_sound and (event == 'TimerRestComplete' or not play_rest_sound):
            self._audio_player.stop()     # In case it was ticking or playing rest music
            alarm_file = self._settings.get('Application.alarm_sound_file')
            self._reset()
            self._set_volume('Application.alarm_sound_volume')
            self._audio_player.setSource(alarm_file)
            self._audio_player.setLoops(1)
            self._audio_player.play()

        # Rest music
        if event == 'TimerWorkComplete':
            self._start_rest_sound()

    def _start_ticking(self, event: str = None, **kwargs) -> None:
        play_tick_sound = (self._settings.get('Application.play_tick_sound') == 'True')
        if play_tick_sound:
            self._audio_player.stop()     # Just in case
            tick_file = self._settings.get('Application.tick_sound_file')
            self._reset()
            self._set_volume('Application.tick_sound_volume')
            self._audio_player.setSource(tick_file)
            self._audio_player.setLoops(QMediaPlayer.Loops.Infinite)
            self._audio_player.play()

    def _start_rest_sound(self) -> None:
        play_rest_sound = (self._settings.get('Application.play_rest_sound') == 'True')
        if play_rest_sound:
            self._audio_player.stop()     # In case it was ticking
            rest_file = self._settings.get('Application.rest_sound_file')
            self._reset()
            self._set_volume('Application.rest_sound_volume')
            self._audio_player.setSource(rest_file)
            self._audio_player.setLoops(1)
            self._audio_player.play()     # This will substitute the bell sound

    def _on_messages(self, event: str, source: AbstractEventSource) -> None:
        if self._timer.is_working():
            self._start_ticking()
        elif self._timer.is_resting():
            self._start_rest_sound()

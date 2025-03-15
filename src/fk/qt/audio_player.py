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
import logging

from PySide6.QtCore import QObject
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QMediaDevices, QAudioDevice
from PySide6.QtWidgets import QWidget

from fk.core.abstract_event_source import AbstractEventSource
from fk.core.abstract_settings import AbstractSettings
from fk.core.event_source_holder import EventSourceHolder, AfterSourceChanged
from fk.core.events import SourceMessagesProcessed, AfterSettingsChanged, TimerWorkStart
from fk.core.pomodoro import POMODORO_TYPE_NORMAL, Pomodoro
from fk.core.timer_data import TimerData

logger = logging.getLogger(__name__)


class AudioPlayer(QObject):
    _audio_output: QAudioOutput | None
    _audio_player: QMediaPlayer | None
    _settings: AbstractSettings
    _source: AbstractEventSource | None

    def __init__(self,
                 parent: QWidget,
                 source_holder: EventSourceHolder,
                 settings: AbstractSettings):
        super().__init__(parent)
        self._source = None
        self._settings = settings
        self._reset()
        source_holder.on(AfterSourceChanged, self._on_source_changed)
        settings.on(AfterSettingsChanged, self._on_setting_changed)

    def _on_source_changed(self, event: str, source: AbstractEventSource):
        if self._audio_player is not None and self._audio_player.isPlaying():
            self._audio_player.stop()
        source.on(SourceMessagesProcessed, lambda **kwargs: self._start_what_is_needed())
        source.on("Timer*Complete", self._play_audio)
        source.on(TimerWorkStart, self._start_ticking)
        self._source = source

    def _on_setting_changed(self, event: str, old_values: dict[str, str], new_values: dict[str, str]):
        needs_reset = False
        for key in new_values.keys():
            if key in ['Application.play_alarm_sound', 'Application.alarm_sound_file', 'Application.alarm_sound_volume',
                       'Application.play_rest_sound', 'Application.rest_sound_file', 'Application.rest_sound_volume',
                       'Application.play_tick_sound', 'Application.tick_sound_file', 'Application.tick_sound_volume',
                       'Application.audio_output']:
                needs_reset = True
        if needs_reset:
            self._reset()
            self._start_what_is_needed()

    def _reset(self):
        found: QAudioDevice = None
        setting: str = self._settings.get('Application.audio_output')
        default: QAudioDevice = None
        for device in QMediaDevices.audioOutputs():
            if device.id().toStdString() == setting:
                found = device
                break
            if device.isDefault():
                default = device
        if found is None and default is not None:
            found = default
            logger.info(f"The previously selected audio device {setting} is not available anymore, "
                        f"switching to default {default.id().toStdString()}")
        if found is None:
            self._audio_output = None
            self._audio_player = None
        else:
            self._audio_output = QAudioOutput(found)
            self._audio_player = QMediaPlayer(self.parent())
            self._audio_player.setAudioOutput(self._audio_output)

    def _set_volume(self, setting: str):
        if self._audio_output is not None:
            try:
                from PySide6.QtMultimedia import QtAudio
                Q = QtAudio
            except Exception:
                from PySide6.QtMultimedia import QAudio
                Q = QAudio
            volume = float(self._settings.get(setting)) / 100.0
            # This is what all mixers do
            volume = Q.convertVolume(volume,
                                     Q.VolumeScale.LogarithmicVolumeScale,
                                     Q.VolumeScale.LinearVolumeScale)
            self._audio_output.setVolume(volume)
            logger.debug(f'Volume is set to {int(volume * 100)}%')

    def _play_audio(self, event: str, pomodoro: Pomodoro, timer: TimerData) -> None:
        if self._audio_player is not None:
            self._audio_player.stop()  # In case it was ticking or playing rest music

            # Alarm bell
            play_alarm_sound = (self._settings.get('Application.play_alarm_sound') == 'True')
            play_rest_sound = (self._settings.get('Application.play_rest_sound') == 'True')
            if play_alarm_sound and (
                event == 'TimerRestComplete'
                or not play_rest_sound
                or (event == 'TimerWorkComplete'
                    and pomodoro.get_type() == POMODORO_TYPE_NORMAL
                    and pomodoro.get_rest_duration() == 0)):    # Long break
                self._reset()

                # We've already checked it, but our audio device could've mysteriously disappeared
                #  in the meantime, setting self._audio_player to None in _reset(). Bug #81 was
                #  reported when this happened due to computer waking up from sleep.
                if self._audio_player is not None:
                    self._set_volume('Application.alarm_sound_volume')
                    alarm_file = self._settings.get('Application.alarm_sound_file')
                    self._audio_player.setSource(alarm_file)
                    self._audio_player.setLoops(1)
                    self._audio_player.play()

            # Rest music, for normal pomodoro only
            if (event == 'TimerWorkComplete'
                    and pomodoro.get_type() == POMODORO_TYPE_NORMAL
                    and pomodoro.get_rest_duration() > 0):  # Normal break
                    self._start_rest_sound()

    def _start_ticking(self, event: str = None, **kwargs) -> None:
        if self._audio_player is not None:
            play_tick_sound = (self._settings.get('Application.play_tick_sound') == 'True')
            if play_tick_sound:
                self._audio_player.stop()     # Just in case
                tick_file = self._settings.get('Application.tick_sound_file')
                self._reset()

                # See comment in _play_audio()
                if self._audio_player is not None:
                    self._set_volume('Application.tick_sound_volume')
                    self._audio_player.setSource(tick_file)
                    self._audio_player.setLoops(QMediaPlayer.Loops.Infinite)
                    self._audio_player.play()

    def _start_rest_sound(self) -> None:
        if self._audio_player is not None:
            play_rest_sound = (self._settings.get('Application.play_rest_sound') == 'True')
            if play_rest_sound:
                self._audio_player.stop()     # In case it was ticking
                rest_file = self._settings.get('Application.rest_sound_file')
                self._reset()

                # See comment in _play_audio()
                if self._audio_player is not None:
                    self._set_volume('Application.rest_sound_volume')
                    self._audio_player.setSource(rest_file)
                    self._audio_player.setLoops(1)
                    self._audio_player.play()     # This will substitute the bell sound

    def _start_what_is_needed(self) -> None:
        if self._source is not None:
            timer = self._source.get_data().get_current_user().get_timer()
            if timer.is_working():
                self._start_ticking()
            elif timer.is_resting() and timer.get_running_pomodoro().get_type() == POMODORO_TYPE_NORMAL:
                self._start_rest_sound()


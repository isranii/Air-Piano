#-------------------------------------------------------------------------------
# Name:        AIR PIANOO
# Purpose:
#
# Author:      Jahnavi Israni
#
# Created:     12-05-2025
# Copyright:   (c) Jahnavi Israni 2025
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import cv2
import threading
import pygame.mixer
import pygame.midi
import time
import math
import numpy as np
from cvzone.HandTrackingModule import HandDetector
import os
import json
from datetime import datetime
import pygame.midi as midi # Import midi specifically for potential MidiException

# --- Main Enhanced Air Piano Class ---
class EnhancedAirPiano:
    # --- UI related constants for better readability and maintainability ---
    UI_HEIGHT_RATIO = 0.3 # UI panel takes up 30% of screen height
    KEY_ASPECT_RATIO = 0.5 # Width/Height ratio of individual piano keys (e.g., 100px wide, 200px high)
    KEY_SPACING_RATIO = 0.01 # Spacing between keys as a ratio of screen width
    UI_KEY_VERTICAL_PADDING = 30 # Vertical padding inside UI panel for keys
    MIN_KEY_WIDTH = 50 # Minimum pixel width for keys to prevent them from becoming too small

    def __init__(self):
        # --- Pygame and MIDI Initialization ---
        # Initialize pygame mixer for potential future audio sample use
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()

        # Initialize pygame MIDI for synth communication
        pygame.midi.init()

        # --- Screen and Display Settings ---
        self.fullscreen = False
        self.window_name = "Enhanced Air Piano"
        self.screen_width = 1280  # Default width, will be updated by camera or fullscreen toggle
        self.screen_height = 720  # Default height

        # --- Audio Settings ---
        self.current_instrument = 0
        self.instruments = {
            0: "Acoustic Grand Piano", 1: "Electric Piano", 4: "Rhodes Piano",
            6: "Harpsichord", 8: "Celesta", 11: "Vibraphone", 12: "Marimba",
            14: "Tubular Bells", 16: "Hammond Organ", 25: "Acoustic Guitar",
            40: "Violin", 48: "String Ensemble", 73: "Flute", 80: "Lead Synth"
        }

        # Initialize MIDI player
        self.player = None  # Will be set in setup_midi
        self.setup_midi()

        # --- Camera Setup ---
        self.cap = None  # Will be set in setup_camera
        self.setup_camera()

        # Update internal screen dimensions based on actual camera resolution if successfully set
        if self.cap and self.cap.isOpened():
            self.screen_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.screen_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # --- Hand Detector Initialization ---
        self.detector = HandDetector(detectionCon=0.8, maxHands=2)

        # --- Chord Mappings and Scales ---
        self.current_scale = "D_Major"
        self.scales = {
            "D_Major": {
                "left": {
                    "thumb": [62, 66, 69],    # D Major
                    "index": [64, 67, 71],    # E Minor
                    "middle": [66, 69, 73],   # F# Minor
                    "ring": [67, 71, 74],     # G Major
                    "pinky": [69, 73, 76]     # A Major
                },
                "right": {
                    "thumb": [74, 78, 81],    # D Major (higher octave)
                    "index": [76, 79, 83],    # E Minor
                    "middle": [78, 81, 85],   # F# Minor
                    "ring": [79, 83, 86],     # G Major
                    "pinky": [81, 85, 88]     # A Major
                }
            },
            "C_Major": {
                "left": {
                    "thumb": [60, 64, 67],    # C Major
                    "index": [62, 65, 69],    # D Minor
                    "middle": [64, 67, 71],   # E Minor
                    "ring": [65, 69, 72],     # F Major
                    "pinky": [67, 71, 74]     # G Major
                },
                "right": {
                    "thumb": [72, 76, 79],    # C Major (higher)
                    "index": [74, 77, 81],    # D Minor
                    "middle": [76, 79, 83],    # E Minor
                    "ring": [77, 81, 84],     # F Major
                    "pinky": [79, 83, 86]     # G Major
                }
            },
            "Pentatonic": { # C Pentatonic Major
                "left": {
                    "thumb": [60, 64, 67],    # C Major
                    "index": [62, 67, 69],    # D Sus
                    "middle": [64, 69, 72],   # E Min
                    "ring": [67, 72, 74],     # G Major
                    "pinky": [69, 74, 77]     # A Minor
                },
                "right": {
                    "thumb": [72, 76, 79],    # C Major (higher)
                    "index": [74, 79, 81],    # D Sus
                    "middle": [76, 81, 84],   # E Min
                    "ring": [79, 84, 86],     # G Major
                    "pinky": [81, 86, 89]     # A Minor
                }
            }
        }

        # --- Visual Settings (Colors) ---
        self.colors = {
            'background': (20, 20, 30), 'active_key': (0, 255, 150), # Greenish-blue for active
            'inactive_key': (60, 60, 80), 'border': (100, 100, 120),
            'text': (255, 255, 255), 'accent': (255, 100, 50), # Orange accent
            'recording': (255, 50, 50), 'pinch_highlight': (0, 255, 255) # Red for recording, yellow for pinch
        }

        # --- State Tracking Variables ---
        # prev_states: Tracks the previous finger-up/down state for gesture detection (0: down, 1: up)
        self.prev_states = {hand_type: {finger: 0 for finger in self.scales[self.current_scale][hand_type]} for hand_type in self.scales[self.current_scale]}

        # active_notes: Tracks individual MIDI notes currently being played (i.e., 'note_on' sent and 'note_off' not yet).
        # This is the source of truth for *audible* notes, including those sustained.
        self.active_notes = set()

        # active_keys: Tracks which visual piano keys should be highlighted based on active finger gestures.
        # This reflects the user's *input* (finger currently up), not necessarily the sustained sound.
        self.active_keys = set()

        # --- Performance Settings ---
        self.sustain_time = 0.8 # How long notes sustain after finger is lowered
        self.velocity_multiplier = 1.0 # Global volume adjustment

        # --- Recording Functionality ---
        self.recording = False
        self.recorded_notes = [] # List of {'note', 'velocity', 'time', 'action'} dictionaries
        self.recording_start_time = None

        # --- Special Effects ---
        self.reverb_enabled = True # Placeholder (MIDI doesn't directly control reverb on generic synths)
        self.echo_enabled = False # Echo is implemented as timed note-on events

        # --- Gesture Settings ---
        self.pinch_threshold = 30 # Pixel distance for pinch detection
        self.pinch_chord_notes = [84, 88, 91]  # High C Major chord for pinch effect
        self.pinch_chord_playing = False # Tracks if the pinch chord is currently triggered

        # --- Performance Metrics ---
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.current_fps = 0

        print("🎹 Enhanced Air Piano Initialized!")
        self.print_controls()

    def setup_midi(self):
        """
        Sets up the MIDI output device.
        Prioritizes unopened software synthesizers for reliable playback.
        Includes specific error handling for device instantiation.
        """
        try:
            midi_devices = []
            for i in range(pygame.midi.get_count()):
                r = pygame.midi.get_device_info(i)
                (interface, name, is_input, is_output, opened) = r
                if is_output: # Consider all output devices
                    midi_devices.append((i, name.decode('utf-8'), opened))

            if not midi_devices:
                raise Exception("No MIDI output devices available.")

            # List of preferred software synthesizers (case-insensitive search)
            preferred_device_names = ['Microsoft GS Wavetable', 'FluidSynth', 'TiMidity', 'loopMIDI', 'Synth']
            best_device_id = -1
            best_device_name = "None"

            # 1. Try to find an unopened preferred device
            for device_id, device_name, opened in midi_devices:
                if not opened:
                    for preferred in preferred_device_names:
                        if preferred.lower() in device_name.lower():
                            best_device_id = device_id
                            best_device_name = device_name
                            break
                    if best_device_id != -1: # Found a preferred, unopened device
                        break

            # 2. If no unopened preferred, try any unopened device
            if best_device_id == -1:
                for device_id, device_name, opened in midi_devices:
                    if not opened:
                        best_device_id = device_id
                        best_device_name = device_name
                        break

            # 3. If still no unopened, use the first available device (even if opened by another app)
            if best_device_id == -1 and midi_devices:
                best_device_id, best_device_name, _ = midi_devices[0]

            if best_device_id == -1:
                 raise Exception("No suitable MIDI output device found after exhaustive search.")

            # --- Critical: Specific error handling for opening the chosen MIDI device ---
            try:
                self.player = pygame.midi.Output(best_device_id)
                self.player.set_instrument(self.current_instrument)
                print(f"✅ MIDI initialized with device: {best_device_name}")
            except midi.MidiException as midi_e:
                print(f"❌ MIDI device '{best_device_name}' failed to open. Error: {midi_e}")
                print("🔧 This device might be in use, have driver issues, or require a restart. Please check your MIDI setup.")
                exit() # Fatal error, cannot proceed without MIDI

        except Exception as e:
            print(f"❌ MIDI initialization failed: {e}")
            print("🔧 Ensure you have a software synthesizer (e.g., FluidSynth with Qsynth/Timidity) or a MIDI device connected and configured.")
            exit() # Fatal error, cannot proceed without MIDI

    def setup_camera(self):
        """
        Sets up the camera, attempting multiple common resolutions for better hand tracking.
        Exits if no camera is found or can't be opened.
        """
        self.cap = cv2.VideoCapture(0) # Attempt to open default camera (index 0)
        if not self.cap.isOpened():
            print("❌ Camera initialization failed. Check if camera is connected, powered on, and not in use by another application.")
            exit()

        resolutions = [(1920, 1080), (1280, 720), (1024, 768), (640, 480)]
        found_resolution = False
        for width, height in resolutions:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            if actual_width == width and actual_height == height:
                print(f"✅ Camera resolution set to {width}x{height}")
                self.screen_width = int(actual_width)
                self.screen_height = int(actual_height)
                found_resolution = True
                break

        if not found_resolution:
            print(f"⚠️ Could not set desired resolution. Using default: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
            self.screen_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.screen_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Set camera properties for better performance/latency
        self.cap.set(cv2.CAP_PROP_FPS, 30) # Attempt to set 30 frames per second
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Reduce buffer size to minimize latency

    def print_controls(self):
        """Prints application control instructions to the console."""
        print("\n🎹 ENHANCED AIR PIANO CONTROLS:")
        print("=" * 40)
        print("✋ Hand Gestures:")
        print("  • Raise fingers to play chords (visual key indicates active input).")
        print("  • Pinch (thumb + index) for special effects (high C Major chord + pitch bend).")
        print("\n⌨️  Keyboard Controls:")
        print("  • 'q'   - Quit application")
        print("  • 'f'   - Toggle fullscreen mode")
        print("  • '1-9' - Change instruments (e.g., '1' for Piano, '2' for Electric Piano)")
        print("  • 's'   - Cycle through musical scales (D Major, C Major, Pentatonic)")
        print("  • 'r'   - Start/stop recording your performance")
        print("  • 'p'   - Playback recorded performance")
        print("  • '+'   - Increase volume (MIDI velocity multiplier)")
        print("  • '-'   - Decrease volume (MIDI velocity multiplier)")
        print("  • 'e'   - Toggle echo effect for chords")
        print("=" * 40)

    def get_current_chords(self):
        """Retrieves chord mappings for the currently selected scale."""
        return self.scales[self.current_scale]

    def calculate_dynamic_velocity(self, hand_landmarks, finger_index):
        """
        Calculates a dynamic MIDI velocity (volume) based on the distance
        between a finger tip and its base joint. A wider separation implies
        a 'stronger' or more deliberate press.
        """
        if not hand_landmarks or len(hand_landmarks) <= 20:
            return 80 # Default velocity if landmarks are missing or incomplete

        # Define landmark indices for finger tip and its corresponding base joint
        # (Thumb: tip 4, base 2), (Index: tip 8, base 5), (Middle: tip 12, base 9),
        # (Ring: tip 16, base 13), (Pinky: tip 20, base 17)
        finger_landmarks = {
            0: (4, 2), 1: (8, 5), 2: (12, 9), 3: (16, 13), 4: (20, 17)
        }

        if finger_index not in finger_landmarks:
            return 80 # Default if finger_index is out of range

        tip_idx, base_idx = finger_landmarks[finger_index]
        tip_pos = hand_landmarks[tip_idx][:2] # (x, y) coordinates
        base_pos = hand_landmarks[base_idx][:2]

        # Calculate Euclidean distance between tip and base
        distance = math.sqrt((tip_pos[0] - base_pos[0])**2 + (tip_pos[1] - base_pos[1])**2)

        # Map distance to normalized 0-1 range (0=min_dist, 1=max_dist)
        # Adjust min_dist/max_dist based on typical hand sizes and camera distance for best results
        min_dist, max_dist = 20, 150 # These values may need calibration for your setup
        normalized = np.clip((distance - min_dist) / (max_dist - min_dist), 0, 1)

        # Apply a non-linear curve (e.g., exponential) to make response more sensitive at lower distances
        velocity_curve = normalized ** 0.6 # Power less than 1 makes smaller movements have greater velocity impact

        # Map to MIDI velocity range (20-127) and apply global volume multiplier
        velocity = int(20 + velocity_curve * 107 * self.velocity_multiplier) # 107 is (127-20)
        return np.clip(velocity, 20, 127) # Ensure velocity stays within valid MIDI range [0-127]

    def play_chord_enhanced(self, chord_notes, velocity):
        """
        Plays a chord by sending 'note_on' MIDI messages for each note in the chord.
        Adds notes to self.active_notes to track currently sounding notes.
        Includes an optional echo effect.
        """
        for i, note in enumerate(chord_notes):
            # Only play note if it's not already active to prevent re-triggering 'note_on' for a held note
            if note not in self.active_notes:
                self.play_single_note(note, velocity)
                self.active_notes.add(note) # Mark note as active (sounding)

                # Echo effect: play the same note again after short delays
                # Trigger echo only for the first note of the chord to avoid excessive echoes
                if self.echo_enabled and i == 0:
                    # Echo notes are also added to active_notes so they are tracked for stopping
                    threading.Timer(0.08, lambda n=note, v=velocity: (self.play_single_note(n, int(v * 0.7)), self.active_notes.add(n))).start()
                    threading.Timer(0.16, lambda n=note, v=velocity: (self.play_single_note(n, int(v * 0.4)), self.active_notes.add(n))).start()

                # Record the 'note_on' event if recording is active
                if self.recording:
                    self.recorded_notes.append({
                        'note': note,
                        'velocity': velocity,
                        'time': time.time() - self.recording_start_time,
                        'action': 'on'
                    })

    def play_single_note(self, note, velocity):
        """Sends a single 'note_on' MIDI message to the synthesizer."""
        if self.player:
            self.player.note_on(note, velocity)

    def stop_chord_enhanced(self, chord_notes):
        """
        Initiates the stopping of a chord's notes after a defined sustain time.
        Notes are removed from self.active_notes only when they are actually turned off.
        """
        def stop_after_delay():
            time.sleep(self.sustain_time) # Wait for the sustain duration
            for note in chord_notes:
                if note in self.active_notes: # Only turn off if the note is still marked as active
                    if self.player:
                        self.player.note_off(note, 127) # Send 'note_off' message (velocity 127 is standard)
                    self.active_notes.discard(note) # Remove from active_notes set

                    # Record the 'note_off' event if recording is active
                    if self.recording:
                        self.recorded_notes.append({
                            'note': note,
                            'velocity': 0, # Velocity 0 indicates note off
                            'time': time.time() - self.recording_start_time,
                            'action': 'off'
                        })

        # Start a new daemon thread for delayed note off to avoid blocking the main video processing loop
        threading.Thread(target=stop_after_delay, daemon=True).start()

    def handle_pinch_gesture(self, hand, img):
        """
        Detects a pinch gesture (thumb and index finger tips close together).
        If detected, plays a special chord and applies pitch bend based on hand's X position.
        Provides visual feedback for the pinch.
        """
        if not hand['lmList'] or len(hand['lmList']) < 21:
            return False # Not enough landmarks for reliable pinch detection

        thumb_tip = hand['lmList'][4][:2]
        index_tip = hand['lmList'][8][:2]
        pinch_dist = math.sqrt((thumb_tip[0] - index_tip[0])**2 + (thumb_tip[1] - index_tip[1])**2)

        # Check if thumb and index are both detected as 'up' AND their distance is below the pinch threshold
        fingers_up = self.detector.fingersUp(hand)
        is_pinching = (pinch_dist < self.pinch_threshold and
                       len(fingers_up) >= 2 and fingers_up[0] == 1 and fingers_up[1] == 1)

        if is_pinching:
            if not self.pinch_chord_playing:
                # Play the special pinch chord if it's not already playing
                for note in self.pinch_chord_notes:
                    if note not in self.active_notes: # Avoid re-triggering if already active
                        self.play_single_note(note, 120) # Play with high velocity
                        self.active_notes.add(note)
                        if self.recording:
                             self.recorded_notes.append({'note': note, 'velocity': 120,
                                                         'time': time.time() - self.recording_start_time, 'action': 'on'})
                self.pinch_chord_playing = True

            # Apply pitch bend: map the hand's horizontal position to the MIDI pitch bend range
            x, y, w, h = hand["bbox"] # Bounding box of the hand
            center_x = x + w // 2 # Horizontal center of the hand

            normalized_x = np.clip(center_x / self.screen_width, 0, 1) # Normalize X to 0-1 range

            # Map normalized X to MIDI pitch bend range (0 = min bend, 8192 = no bend, 16383 = max bend)
            pitch_bend_value = int(normalized_x * 16383)
            self.send_pitch_bend(pitch_bend_value)

            # Provide visual feedback for the active pinch gesture
            cv2.circle(img, (center_x, y + h // 2), 30, self.colors['pinch_highlight'], -1)
            cv2.circle(img, (center_x, y + h // 2), 35, (255, 255, 0), 3)
            cv2.putText(img, "PITCH BEND", (center_x - 60, y + h // 2 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['text'], 2, cv2.LINE_AA)
            return True # Indicate that a pinch was handled by this hand
        else:
            return False # Indicate no pinch was detected for this hand

    def send_pitch_bend(self, bend_value):
        """Sends a pitch bend MIDI message to the synthesizer."""
        if self.player:
            # MIDI pitch bend message format:
            # Status byte: 0xE0 (for MIDI Channel 0) to 0xEF (for MIDI Channel 15)
            # Data byte 1 (LSB): Least Significant Byte of the 14-bit bend value
            # Data byte 2 (MSB): Most Significant Byte of the 14-bit bend value
            lsb = bend_value & 0x7F # Extract lower 7 bits
            msb = (bend_value >> 7) & 0x7F # Extract upper 7 bits
            self.player.write_short(0xE0, lsb, msb) # Send on MIDI Channel 0

    def draw_enhanced_ui(self, img):
        """
        Draws the comprehensive user interface on the video frame,
        including piano keys, information panel, and performance metrics.
        """
        height, width = img.shape[:2]

        # Update current screen dimensions for dynamic UI calculations based on actual frame size
        self.screen_width = width
        self.screen_height = height
        self.ui_height = int(height * self.UI_HEIGHT_RATIO)

        # Create a semi-transparent overlay for the UI background for a modern look
        overlay = img.copy()
        cv2.rectangle(overlay, (0, height - self.ui_height), (width, height),
                      self.colors['background'], -1) # Draw solid background
        cv2.addWeighted(overlay, 0.8, img, 0.2, 0, img) # Blend overlay with main image

        # Draw main UI components
        self.draw_piano_keys_enhanced(img)
        self.draw_info_panel(img, width, height)
        self.draw_performance_metrics(img, width)

    def draw_piano_keys_enhanced(self, img):
        """
        Draws dynamically sized piano keys at the bottom of the screen.
        Key highlights reflect the user's current finger input (active_keys).
        """
        num_keys = 10 # 5 keys per hand (thumb to pinky)

        # Calculate dynamic key spacing based on screen width
        key_spacing = int(self.screen_width * self.KEY_SPACING_RATIO)

        # Calculate the available width for all keys, accounting for spacing
        total_keys_available_width = self.screen_width - (num_keys + 1) * key_spacing
        self.key_width = total_keys_available_width // num_keys

        # Ensure key width doesn't fall below a minimum for usability
        if self.key_width < self.MIN_KEY_WIDTH:
            self.key_width = self.MIN_KEY_WIDTH

        # Calculate key height based on desired aspect ratio and available UI space
        self.key_height = int(self.key_width / self.KEY_ASPECT_RATIO)
        # Ensure key height fits within the UI panel, accounting for vertical padding
        if self.key_height > self.ui_height - self.UI_KEY_VERTICAL_PADDING:
            self.key_height = self.ui_height - self.UI_KEY_VERTICAL_PADDING

        # Calculate vertical position of keys to center them within the UI panel
        key_y = self.screen_height - self.ui_height + (self.ui_height - self.key_height) // 2

        # Calculate starting X position to horizontally center the entire set of keys
        total_keys_actual_width = num_keys * self.key_width + (num_keys - 1) * key_spacing
        start_x = (self.screen_width - total_keys_actual_width) // 2
        if start_x < 0: start_x = 0 # Prevent negative start_x if keys somehow become too wide

        chords = self.get_current_chords()
        finger_names = ["thumb", "index", "middle", "ring", "pinky"]

        # --- Draw Left Hand Keys ---
        for i, finger in enumerate(finger_names):
            x = start_x + i * (self.key_width + key_spacing)
            key_name = f"left_{finger}"
            # Choose color based on whether the key is currently active (finger up)
            color = self.colors['active_key'] if key_name in self.active_keys else self.colors['inactive_key']

            cv2.rectangle(img, (x, key_y), (x + self.key_width, key_y + self.key_height), color, -1) # Fill key
            cv2.rectangle(img, (x, key_y), (x + self.key_width, key_y + self.key_height), self.colors['border'], 2) # Key border

            # Add chord name and finger identifier text
            chord_notes = chords["left"][finger]
            chord_name_display = self.get_chord_name(chord_notes)
            cv2.putText(img, chord_name_display, (x + 5, key_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.colors['text'], 1, cv2.LINE_AA) # Increased font size
            cv2.putText(img, f"L{i+1}", (x + 5, key_y + self.key_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['text'], 1, cv2.LINE_AA) # Increased font size

        # --- Draw Right Hand Keys ---
        for i, finger in enumerate(finger_names):
            x = start_x + (i + 5) * (self.key_width + key_spacing) # Offset by 5 keys for right hand
            key_name = f"right_{finger}"
            color = self.colors['active_key'] if key_name in self.active_keys else self.colors['inactive_key']

            cv2.rectangle(img, (x, key_y), (x + self.key_width, key_y + self.key_height), color, -1)
            cv2.rectangle(img, (x, key_y), (x + self.key_width, key_y + self.key_height), self.colors['border'], 2)

            chord_notes = chords["right"][finger]
            chord_name_display = self.get_chord_name(chord_notes)
            cv2.putText(img, chord_name_display, (x + 5, key_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.colors['text'], 1, cv2.LINE_AA)
            cv2.putText(img, f"R{i+1}", (x + 5, key_y + self.key_height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['text'], 1, cv2.LINE_AA)


    def get_chord_name(self, notes):
        """
        Determines a simple chord name (e.g., C Maj, D Min, C4) from a list of MIDI notes.
        This is a heuristic and can be expanded for more complex chord types.
        """
        if not notes:
            return "---"

        sorted_notes = sorted(notes)
        root_midi = sorted_notes[0]
        # Get raw note name (e.g., "C4"), then strip octave for cleaner display on key
        root_name_raw = MusicTheoryHelper.note_to_name(root_midi)
        root_name = ''.join([char for char in root_name_raw if not char.isdigit() and char not in ['-', '+']])

        if len(sorted_notes) == 1:
            return f"{root_name}" # For single notes, just show the note name

        if len(sorted_notes) == 2:
            # Simple interval naming for two notes
            interval = sorted_notes[1] - sorted_notes[0]
            if interval == 3: return f"{root_name} m3" # Minor 3rd
            if interval == 4: return f"{root_name} M3" # Major 3rd
            if interval == 7: return f"{root_name} P5" # Perfect 5th
            return f"{root_name} Pair" # Generic for other 2-note combinations

        if len(sorted_notes) >= 3:
            # Check for common triad intervals from the root
            interval1 = sorted_notes[1] - sorted_notes[0]
            interval2 = sorted_notes[2] - sorted_notes[1]

            if interval1 == 4 and interval2 == 3: # Root, Major 3rd, Perfect 5th
                return f"{root_name} Maj"
            elif interval1 == 3 and interval2 == 4: # Root, Minor 3rd, Perfect 5th
                return f"{root_name} Min"
            elif interval1 == 5 and interval2 == 2: # e.g., C-F-G (C Sus4)
                return f"{root_name} Sus4"
            elif interval1 == 2 and interval2 == 5: # e.g., C-D-G (C Sus2)
                return f"{root_name} Sus2"
            else:
                return f"{root_name} Triad" # Generic for other 3-note combinations
        return "Chord" # Fallback for other note combinations

    def draw_info_panel(self, img, width, height):
        """
        Draws the information panel displaying current settings,
        the 'Chord Input' (based on finger gestures), and 'MIDI Output' (active notes).
        """
        info_x = 20
        info_y_start = 30 # Starting Y position for info text
        line_height = 25 # Vertical spacing between lines

        # --- Current Settings Display ---
        info_text_lines = [
            f"Scale: {self.current_scale.replace('_', ' ')}",
            f"Instrument: {self.instruments.get(self.current_instrument, 'Unknown')}",
            f"Volume: {int(self.velocity_multiplier * 100)}%",
            f"Recording: {'ON' if self.recording else 'OFF'}",
            f"Effects: {'Echo' if self.echo_enabled else 'Clean'}"
        ]

        # --- Enhanced "Chord Input" Display (based on active finger gestures) ---
        current_input_chord_name = "None"
        if self.active_keys: # If any visual keys are currently active from finger input
            combined_input_notes = set()
            chords_data = self.get_current_chords()

            for key_name in self.active_keys:
                # Extract hand_type (left/right) and finger_name (thumb/index etc.)
                hand_type, finger_name = key_name.split('_')
                if hand_type in chords_data and finger_name in chords_data[hand_type]:
                    # Add all notes from the chord mapped to this active finger to a combined set
                    combined_input_notes.update(chords_data[hand_type][finger_name])

            if combined_input_notes:
                # Use get_chord_name to attempt to identify the chord from the combined input notes
                current_input_chord_name = self.get_chord_name(list(combined_input_notes))

        info_text_lines.append(f"Chord Input: {current_input_chord_name}")

        # --- "MIDI Output" Display (individual active MIDI notes currently sounding) ---
        active_note_names = sorted([MusicTheoryHelper.note_to_name(note) for note in self.active_notes])
        active_notes_str = ", ".join(active_note_names)
        if len(active_notes_str) > 50: # Limit string length for display
            active_notes_str = active_notes_str[:47] + "..." # Truncate if too long
        info_text_lines.append(f"MIDI Output: {active_notes_str if active_notes_str else 'None'}")

        # Draw each line of information text
        for i, text in enumerate(info_text_lines):
            color = self.colors['recording'] if 'Recording: ON' in text else self.colors['text']
            cv2.putText(img, text, (info_x, info_y_start + i * line_height),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

    def draw_performance_metrics(self, img, width):
        """Draws the FPS counter on the top right of the screen."""
        cv2.putText(img, f"FPS: {self.current_fps}", (width - 100, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['accent'], 2, cv2.LINE_AA)

    def update_fps(self):
        """Updates the frames per second (FPS) counter every second."""
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.fps_timer >= 1.0: # Check if one second has passed
            self.current_fps = self.fps_counter
            self.fps_counter = 0
            self.fps_timer = current_time

    def handle_keyboard_input(self, key):
        """Handles various keyboard controls for application settings."""
        if key == ord('f'):
            self.toggle_fullscreen()
        elif key == ord('s'):
            self.cycle_scale()
        elif key == ord('r'):
            self.toggle_recording()
        elif key == ord('p'):
            self.playback_recording()
        elif key == ord('e'):
            self.echo_enabled = not self.echo_enabled
            print(f"Echo effect: {'ON' if self.echo_enabled else 'OFF'}")
        elif key == ord('+') or key == ord('='): # '+' and '=' share a key on many keyboards
            self.velocity_multiplier = min(2.0, self.velocity_multiplier + 0.1)
            print(f"Volume: {int(self.velocity_multiplier * 100)}%")
        elif key == ord('-'):
            self.velocity_multiplier = max(0.1, self.velocity_multiplier - 0.1)
            print(f"Volume: {int(self.velocity_multiplier * 100)}%")
        elif ord('1') <= key <= ord('9'): # Keys '1' through '9' for instrument selection
            instrument_keys = list(self.instruments.keys())
            idx = key - ord('1') # Convert ASCII key code to 0-8 index
            if idx < len(instrument_keys):
                self.current_instrument = instrument_keys[idx]
                if self.player:
                    self.player.set_instrument(self.current_instrument)
                print(f"Instrument: {self.instruments[self.current_instrument]}")

    def toggle_fullscreen(self):
        """Toggles fullscreen mode for the display window."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            # Set window property to fullscreen
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            # Set window property back to normal (windowed)
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

        # Update internal screen dimensions after fullscreen toggle as window size may change
        time.sleep(0.1) # Give OS a moment to adjust window size
        self.screen_width = int(cv2.getWindowImageRect(self.window_name)[2])
        self.screen_height = int(cv2.getWindowImageRect(self.window_name)[3])


    def cycle_scale(self):
        """Cycles through the available musical scales."""
        scales = list(self.scales.keys())
        current_idx = scales.index(self.current_scale)
        self.current_scale = scales[(current_idx + 1) % len(scales)] # Move to next scale circularly

        # Reset previous finger states for the new scale to avoid stuck notes/keys visually
        self.prev_states = {hand_type: {finger: 0 for finger in self.scales[self.current_scale][hand_type]} for hand_type in self.scales[self.current_scale]}
        self.active_keys.clear() # Clear any active visual keys

        print(f"Scale changed to: {self.current_scale.replace('_', ' ')}")

    def toggle_recording(self):
        """Starts or stops recording MIDI events."""
        if not self.recording:
            self.recording = True
            self.recorded_notes = [] # Clear any previous recording to start fresh
            self.recording_start_time = time.time() # Mark start time of recording
            print("🔴 Recording started...")
        else:
            self.recording = False
            print(f"⏹️ Recording stopped. Captured {len(self.recorded_notes)} events.")

    def playback_recording(self):
        """Plays back the recorded MIDI events in a separate thread."""
        if not self.recorded_notes:
            print("No recording to playback.")
            return

        # Prevent starting multiple playback threads simultaneously
        if hasattr(self, '_playback_thread') and self._playback_thread.is_alive():
            print("Playback already in progress. Please wait for it to finish.")
            return

        def playback_thread_func():
            print("▶️ Playing back recording...")
            start_playback_time = time.time()

            # Stop any currently active notes before starting playback to avoid clashes
            for note in list(self.active_notes):
                if self.player:
                    self.player.note_off(note, 127)
                self.active_notes.discard(note)
            self.active_keys.clear() # Clear visual active keys during playback

            for event in self.recorded_notes:
                # Wait until the precise timing of the event in the recording
                target_time = start_playback_time + event['time']
                while time.time() < target_time:
                    time.sleep(0.001) # Small sleep to yield CPU, prevent busy-waiting

                # Play or stop the note based on the recorded action
                if event['action'] == 'on':
                    if self.player:
                        self.player.note_on(event['note'], event['velocity'])
                    self.active_notes.add(event['note']) # Mark as active during playback
                else: # action == 'off'
                    if self.player:
                        self.player.note_off(event['note'], event['velocity'])
                    self.active_notes.discard(event['note']) # Mark as inactive during playback

            # Ensure all notes are off after the recording finishes playback
            for note in list(self.active_notes):
                if self.player:
                    self.player.note_off(note, 127)
                self.active_notes.discard(note)
            print("✅ Playback complete.")

        # Create and start the playback thread as a daemon so it exits with the main program
        self._playback_thread = threading.Thread(target=playback_thread_func, daemon=True)
        self._playback_thread.start()

    def process_hands(self, hands, img):
        """
        Processes detected hands to trigger piano notes based on finger gestures.
        Updates `self.active_keys` for visual feedback based on current finger states.
        Handles pinch gestures separately.
        """
        chords = self.get_current_chords()
        # Initialize current finger states for this frame
        current_finger_states = {hand_type: {finger: 0 for finger in chords[hand_type]} for hand_type in chords}

        # Temporary set to hold keys active (finger up) in the current frame's input
        current_frame_active_keys_input = set()

        pinching_in_current_frame = False

        for hand in hands:
            hand_type_detected = hand["type"] # "Left" or "Right"
            hand_key = "left" if hand_type_detected == "Left" else "right"

            # 1. First, check for pinch gesture for this hand
            if self.handle_pinch_gesture(hand, img):
                pinching_in_current_frame = True
                # If a hand is performing a pinch, we assume it's for a special effect
                # and skip processing its regular finger-based chord detection for this frame.
                continue

            # 2. If not pinching, process regular finger-based chord detection for this hand
            fingers_up_list = self.detector.fingersUp(hand) # List of 0s and 1s for fingers being up/down
            finger_names = ["thumb", "index", "middle", "ring", "pinky"]

            for i, finger_name in enumerate(finger_names):
                # Ensure the finger exists in the current scale's chord mapping and is detected by cvzone
                if finger_name in chords[hand_key] and i < len(fingers_up_list):
                    current_finger_states[hand_key][finger_name] = fingers_up_list[i]
                    key_name = f"{hand_key}_{finger_name}"

                    # Detect a finger being raised (transition from down (0) to up (1))
                    if (current_finger_states[hand_key][finger_name] == 1 and
                        self.prev_states[hand_key][finger_name] == 0):

                        velocity = self.calculate_dynamic_velocity(hand['lmList'], i)
                        self.play_chord_enhanced(chords[hand_key][finger_name], velocity)
                        current_frame_active_keys_input.add(key_name) # Add to visual key set

                    # Detect a finger being lowered (transition from up (1) to down (0))
                    elif (current_finger_states[hand_key][finger_name] == 0 and
                          self.prev_states[hand_key][finger_name] == 1):
                        self.stop_chord_enhanced(chords[hand_key][finger_name])

                    # If finger is still raised (no state change, but still active input)
                    if current_finger_states[hand_key][finger_name] == 1:
                        current_frame_active_keys_input.add(key_name)

        # Update the master `self.active_keys` set for visual feedback
        # This set will contain only the keys whose corresponding fingers are currently detected as 'up'.
        self.active_keys = current_frame_active_keys_input

        # Handle pinch chord stopping: If pinch was playing but no longer detected in *any* hand in this frame
        if not pinching_in_current_frame and self.pinch_chord_playing:
            # Immediately stop the notes associated with the pinch chord
            for note in self.pinch_chord_notes:
                if note in self.active_notes: # Only turn off if the note is still active
                    if self.player:
                        self.player.note_off(note, 127)
                    self.active_notes.discard(note) # Remove from active_notes immediately
            self.pinch_chord_playing = False # Reset pinch state
            self.send_pitch_bend(8192)  # Reset pitch bend to center (no bend)

        # Update previous states for the next frame's detection
        self.prev_states = current_finger_states

    def run(self):
        """
        Main application loop. Reads camera frames, processes hands,
        updates UI, and handles user input.
        """
        print("\n🎹 Starting Enhanced Air Piano...")
        # Create the OpenCV window and set it to normal size initially
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.screen_width, self.screen_height)

        try:
            while True:
                success, img = self.cap.read() # Read a frame from the camera
                if not success:
                    print("❌ Failed to read from camera. Retrying...")
                    time.sleep(0.1) # Short delay before retrying
                    continue

                img = cv2.flip(img, 1)  # Mirror the image for a more natural user experience

                # Detect hands and draw landmarks on the frame
                hands, img = self.detector.findHands(img, draw=True)

                if hands:
                    # If hands are detected, process them to trigger notes/gestures
                    self.process_hands(hands, img)
                else:
                    # If no hands are detected in the current frame:
                    # 1. Reset all previous finger states to 'down'
                    self.prev_states = {hand_type: {finger: 0 for finger in self.get_current_chords()[hand_type]} for hand_type in self.get_current_chords()}

                    # 2. Clear all visual active keys on the UI
                    self.active_keys.clear()

                    # 3. Stop all currently active MIDI notes to prevent stuck notes
                    for note in list(self.active_notes): # Iterate over a copy to allow modification
                        if self.player:
                            self.player.note_off(note, 127)
                        self.active_notes.discard(note) # Remove from active_notes set

                    # 4. Reset pinch state and pitch bend if the pinch gesture was active
                    if self.pinch_chord_playing:
                        self.pinch_chord_playing = False
                        self.send_pitch_bend(8192) # Reset pitch bend to neutral position

                # Draw all enhanced UI elements on the current frame
                self.draw_enhanced_ui(img)

                # Update and display the FPS counter
                self.update_fps()

                # Display the processed frame in the window
                cv2.imshow(self.window_name, img)

                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF # Wait for 1ms and get key press
                if key == ord('q'):
                    break # Exit the main loop if 'q' is pressed
                elif key != 255:  # Check if a valid key was pressed (255 means no key pressed)
                    self.handle_keyboard_input(key)

        except KeyboardInterrupt:
            print("\n⏹️ Application interrupted by user (Ctrl+C).")
        except Exception as e:
            print(f"❌ An unexpected error occurred during runtime: {e}")
            import traceback # Print full traceback for detailed debugging
            traceback.print_exc()
        finally:
            self.cleanup() # Ensure all resources are properly released on exit

    def cleanup(self):
        """Cleans up all allocated resources (camera, OpenCV windows, Pygame MIDI/Mixer) on application exit."""
        print("\n🧹 Cleaning up resources...")

        # Stop all currently active MIDI notes to prevent lingering sounds
        for note in list(self.active_notes):
            if self.player:
                self.player.note_off(note, 127)
        self.active_notes.clear()

        # Release the camera capture object
        if self.cap and self.cap.isOpened():
            self.cap.release()

        # Destroy all OpenCV windows
        cv2.destroyAllWindows()

        # Close the MIDI output device and quit Pygame modules
        if self.player:
            self.player.close()
        pygame.midi.quit()
        pygame.mixer.quit()
        print("✅ Enhanced Air Piano closed successfully.")

# --- Additional Utility Classes and Functions ---

class MusicTheoryHelper:
    """Helper class for music theory operations, e.g., converting MIDI notes to names."""
    @staticmethod
    def note_to_name(midi_note):
        """Converts a MIDI note number (0-127) to its musical note name with octave (e.g., 60 -> C4)."""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        # MIDI note 0 is C-1 (octave -1), so C4 is MIDI note 60 (octave 4)
        octave = (midi_note // 12) - 1
        note_name = note_names[midi_note % 12]
        return f"{note_name}{octave}"

    @staticmethod
    def generate_chord_progression(key_root_midi=60, progression_type='I-V-vi-IV'):
        """
        Generates a list of MIDI root notes for a common chord progression in a given key.
        This is a conceptual helper and not directly used in the main piano logic currently.
        """
        # Intervals relative to the root of the I chord (e.g., in C Major: C=0)
        progressions = {
            'I-V-vi-IV': [0, 7, 9, 5],  # C-G-Am-F (relative to C)
            'vi-IV-I-V': [9, 5, 0, 7],  # Am-F-C-G (relative to C)
            'I-vi-IV-V': [0, 9, 5, 7],  # C-Am-F-G (relative to C)
        }

        intervals = progressions.get(progression_type, progressions['I-V-vi-IV'])
        return [key_root_midi + interval for interval in intervals]

class AudioEffects:
    """
    Placeholder class for potential future real-time audio effects processing.
    Note: Real-time audio effects for MIDI output generally require a dedicated
    audio engine or VST host, not just `pygame.midi`, which only sends MIDI data.
    This class serves as an outline for where such functionality might be added
    if you were to process raw audio output (e.g., from an internal synthesizer).
    """
    def __init__(self):
        self.reverb_room_size = 0.5 # Example parameter
        self.delay_time = 0.3 # Example parameter
        self.delay_feedback = 0.4 # Example parameter

    def apply_reverb(self, audio_data):
        """Conceptual method to apply reverb effect to raw audio data."""
        # Implementation would require an audio processing library (e.g., SciPy, Pydub, PyAudio)
        # and working with actual audio samples (numpy arrays of audio data).
        return audio_data # Currently a no-op

    def apply_delay(self, audio_data):
        """Conceptual method to apply delay effect to raw audio data."""
        # As above, this applies to audio samples, not directly to MIDI messages.
        return audio_data # Currently a no-op

# Configuration manager for saving/loading application settings
class ConfigManager:
    """Manages loading and saving application configuration settings to/from a JSON file."""
    @staticmethod
    def save_config(piano_instance, filename='air_piano_config.json'):
        """Saves current application settings to a JSON file."""
        config = {
            'current_scale': piano_instance.current_scale,
            'current_instrument': piano_instance.current_instrument,
            'velocity_multiplier': piano_instance.velocity_multiplier,
            'sustain_time': piano_instance.sustain_time,
            'echo_enabled': piano_instance.echo_enabled,
            'reverb_enabled': piano_instance.reverb_enabled,
            'pinch_threshold': piano_instance.pinch_threshold,
            'screen_width': piano_instance.screen_width, # Save last known window size
            'screen_height': piano_instance.screen_height
        }
        try:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=2) # Use indent for human-readable JSON
            print(f"✅ Configuration saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save config to {filename}: {e}")

    @staticmethod
    def load_config(piano_instance, filename='air_piano_config.json'):
        """Loads configuration settings from a JSON file."""
        try:
            if not os.path.exists(filename):
                raise FileNotFoundError(f"Config file '{filename}' not found.")

            with open(filename, 'r') as f:
                config = json.load(f)

            # Apply loaded settings, providing defaults if a key is missing from the file
            piano_instance.current_scale = config.get('current_scale', 'D_Major')
            piano_instance.current_instrument = config.get('current_instrument', 0)
            piano_instance.velocity_multiplier = config.get('velocity_multiplier', 1.0)
            piano_instance.sustain_time = config.get('sustain_time', 0.8)
            piano_instance.echo_enabled = config.get('echo_enabled', False)
            piano_instance.reverb_enabled = config.get('reverb_enabled', True)
            piano_instance.pinch_threshold = config.get('pinch_threshold', 30)

            # Load screen dimensions, prioritizing them but falling back to current values if not in config
            piano_instance.screen_width = config.get('screen_width', piano_instance.screen_width)
            piano_instance.screen_height = config.get('screen_height', piano_instance.screen_height)

            # Update MIDI instrument if the player object has already been initialized
            if piano_instance.player:
                piano_instance.player.set_instrument(piano_instance.current_instrument)

            print(f"✅ Configuration loaded from {filename}")
        except FileNotFoundError:
            print(f"ℹ️ Config file {filename} not found, using default settings.")
        except json.JSONDecodeError:
            print(f"❌ Error decoding JSON from {filename}. File might be corrupted. Using defaults.")
        except Exception as e:
            print(f"❌ Failed to load config from {filename}: {e}. Using defaults.")

class PerformanceOptimizer:
    """Utilities for optimizing performance, primarily related to camera settings."""
    @staticmethod
    def optimize_camera_settings(cap):
        """
        Attempts to optimize camera settings for better hand tracking performance and consistency.
        Specifically tries to disable auto-exposure and auto-focus which can cause fluctuations.
        """
        if not cap or not cap.isOpened():
            print("⚠️ Cannot optimize camera settings: Camera not initialized or opened.")
            return

        try:
            # Set manual exposure mode and a specific exposure value.
            # Manual exposure reduces flickering due to changing lighting, improving tracking stability.
            # Value of 1 for CAP_PROP_AUTO_EXPOSURE enables manual mode.
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            # CAP_PROP_EXPOSURE value: Negative values typically mean brighter, positive darker.
            # Range varies by camera (-1 to -10, or 0 to 1000s). -6 is a common starting point.
            # Users may need to adjust this value based on their lighting conditions.
            cap.set(cv2.CAP_PROP_EXPOSURE, -6)

            # Disable autofocus for consistent depth and less processing overhead.
            # Autofocus can cause frame pauses or shifts which disrupt tracking.
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # 0 for manual focus
            print("✅ Camera exposure and autofocus optimization attempted.")
        except Exception as e:
            print(f"⚠️ Could not fully optimize camera settings: {e} (Some properties might not be supported by your camera).")

# --- Main Execution Block ---
if __name__ == "__main__":
    piano = EnhancedAirPiano()

    # Load application configuration from file at startup
    ConfigManager.load_config(piano)

    # Apply camera optimization settings (must be called after camera is successfully set up)
    PerformanceOptimizer.optimize_camera_settings(piano.cap)

    # Start the main application loop
    piano.run()

    # Save current configuration settings to file on application exit
    ConfigManager.save_config(piano)
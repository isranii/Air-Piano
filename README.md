# 🎹✨ Air Piano: A Gesture-Controlled Virtual Instrument ✨🎶

Ever envisioned controlling a musical instrument without physical touch? The **Air Piano** is a groundbreaking, touchless virtual instrument that empowers users to create music using intuitive hand gestures captured by a webcam. Built with Python and OpenCV, this project translates your natural movements into expressive piano chords and melodies, offering a unique and magical interface for musical creation.

## Key Features & Capabilities 🚀

The **Enhanced Air Piano** delivers a real-time, interactive musical experience with a robust set of features:

* **Precision Hand & Finger Tracking:** Leveraging `cvzone.HandTrackingModule`, the system accurately detects and interprets nuanced hand and individual finger movements, ensuring low-latency and reliable gesture recognition.
* **Dynamic Chord Playback:** Each distinct finger gesture (thumb, index, middle, ring, pinky) is mapped to specific musical chords within a chosen scale (e.g., D Major, C Major, Pentatonic), enabling intuitive chord triggering.
* **Expressive Control through Gestures:**
    * **Dynamic Velocity (Volume):** MIDI velocity is dynamically calculated based on the distance between a finger's tip and its base joint. A wider separation indicates a more deliberate "press," resulting in a louder, more expressive sound.
    * **Pinch-Activated Pitch Bend:** A unique "pinch" gesture (thumb and index finger proximity) triggers a special high-octave chord. Horizontal hand movement while pinching allows for real-time pitch bending, adding dynamic melodic shifts.
* **Comprehensive MIDI Integration:**
    * **Versatile Instrument Selection:** Users can instantly switch between a wide range of General MIDI instruments (e.g., Acoustic Grand Piano, Electric Piano, Violin, Flute) via simple keyboard commands.
    * **Seamless MIDI Output:** The system efficiently sends `note_on`, `note_off`, and `pitch_bend` messages to any configured software or hardware MIDI synthesizer, ensuring clear and responsive audio output.
* **Interactive User Interface (UI):**
    * **Dynamic On-Screen Keyboard:** A responsive virtual piano keyboard is rendered at the bottom of the display, with keys dynamically highlighted to visually represent actively triggered chords.
    * **Real-time Feedback Panel:** An informative panel provides live updates on the current musical scale, selected instrument, volume level, recording status, and a clear distinction between recognized "Chord Input" gestures and the "MIDI Output" notes currently sounding.
* **Performance Recording and Playback:**
    * **MIDI Event Recording:** The application precisely captures all `note_on` and `note_off` events with accurate timestamps, allowing users to record their air piano performances.
    * **Synchronized Playback:** Recorded sequences can be replayed synchronously, faithfully reproducing the original timing and dynamics of the performance.
* **Configurable Musical Scales:** Users can easily switch between different predefined musical scales to explore various harmonic contexts and expand their compositional possibilities.
* **System Optimization & Persistence:**
    * **Camera Optimization:** The system attempts to optimize webcam settings (e.g., resolution, disabling autofocus) to enhance tracking stability and minimize latency.
    * **Configuration Management:** A `ConfigManager` facilitates saving and loading application settings (e.g., current scale, instrument, volume) to a JSON file, ensuring user preferences persist across sessions.
* **Intuitive Keyboard Controls:** A set of straightforward keyboard shortcuts is provided for essential functions, streamlining the user experience and allowing focus on musical expression.

## Getting Started 🚀

Follow these steps to set up and run the Enhanced Air Piano on your local machine.

### Prerequisites

Before you begin, ensure you have:

1.  **Python 3.x** installed.
2.  A **webcam** connected to your computer.
3.  A **software MIDI synthesizer** configured on your system. This is essential for audio output.
    * **Windows:** "Microsoft GS Wavetable Synth" is typically built-in.
    * **macOS:** "DLS Synth" (may require enabling in Audio MIDI Setup).
    * **Linux:** `FluidSynth` (recommended) with a soundfont (e.g., `FluidR3_GM.sf2`) and an application like `qsynth` or `timidity++`. Ensure it's active and exposed as a MIDI output device.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/isranii/Air-Piano.git](https://github.com/isranii/Air-Piano.git)
    cd Air-Piano
    ```

2.  **Install the required Python packages:**
    ```bash
    pip install opencv-python mediapipe cvzone pygame numpy
    ```

### Running the Application

1.  **Verify MIDI Synthesizer:** Confirm your software MIDI synthesizer is running and accessible.
2.  **Execute the main script:**
    ```bash
    python air_piano.py
    ```
    The webcam feed will appear, indicating the application is ready for interaction.

## Interaction & Controls 🎮

Once the Air Piano window is active, engage with the instrument through gestures and keyboard commands:

### Hand Gestures:

* **✋ Raise a Finger:** Simply lift your thumb, index, middle, ring, or pinky. The corresponding on-screen key will illuminate, and the mapped chord will play.
* **🤏 The Pinch Gesture:** Bring your thumb and index finger together. This will trigger a specific high-octave chord. Moving your hand horizontally while pinching will apply a real-time pitch bend effect to the notes.

### Keyboard Shortcuts:

* **`q`**: Quit the application.
* **`f`**: Toggle fullscreen mode.
* **`1` - `9`**: Change the active MIDI instrument.
* **`s`**: Cycle through available musical scales (D Major, C Major, Pentatonic).
* **`r`**: Start/Stop recording your performance.
* **`p`**: Playback the last recorded performance.
* **`+` / `=`**: Increase overall volume (MIDI velocity multiplier).
* **`-`**: Decrease overall volume (MIDI velocity multiplier).
* **`e`**: Toggle the echo effect for chords.

## Technical Architecture & Design Principles 💡

The **Air Piano** is structured around a robust, object-oriented design, primarily within the `EnhancedAirPiano` class. Key architectural principles include:

* **Modularity:** Complex functionalities are encapsulated into distinct methods for camera control, MIDI communication, UI rendering, gesture processing, and input handling, promoting code clarity and maintainability.
* **Asynchronous Operations:** The application leverages Python's `threading` module for background tasks, such as note sustain, echo effects, and recording playback. This ensures the main video processing loop remains non-blocking and highly responsive.
* **Comprehensive State Management:** The system meticulously tracks `prev_states` for accurate gesture-based note triggering, `active_notes` for currently sounding MIDI notes, and `active_keys` for real-time visual UI feedback. This prevents issues like "stuck notes" and ensures visual-auditory synchronization.
* **Dynamic UI Scaling:** All on-screen UI elements, including the virtual keyboard and info panels, dynamically adjust their size and position based on the detected screen resolution, providing a consistent and aesthetically pleasing user experience.
* **Persistent Configuration:** A `ConfigManager` is implemented to seamlessly save and load user preferences (e.g., current scale, instrument, volume) to a JSON file, ensuring settings are retained across application sessions.

## Future Enhancements & Contributions 🚀

The Air Piano is an evolving project with exciting possibilities for future development. Your contributions are highly valued!

* **Custom Chord Configuration:** Develop a feature that allows users to define and save personalized chord mappings for each finger.
* **Expanded Expressive Gestures:** Investigate and integrate additional hand gestures for fine-grained control over musical parameters such as vibrato, tremolo, or other articulations.
* **Integrated Software Synthesizer:** Explore incorporating a Python-based audio synthesis library to generate sound directly within the application, reducing dependency on external MIDI setups.
* **Advanced Audio Effects (Post-Synthesis):** If an internal synthesizer is implemented, enhance the sound with real-time audio effects like advanced reverb, delay, chorus, or distortion.
* **Machine Learning for Enhanced Expression:** Research and apply more sophisticated machine learning models for gesture interpretation to enable even more nuanced control over dynamics and musical phrasing.
* **Interactive On-Screen Controls:** Implement direct on-screen buttons or sliders that can be controlled via mouse clicks or hand gestures, offering alternative ways to adjust settings like volume, sustain time, or instrument selection.

## Contributing 🤝

Contributions are welcome! If you have suggestions for improvements, new features, or bug fixes, please feel free to open an [issue](https://github.com/isranii/Air-Piano/issues) or submit a [pull request](https://github.com/isranii/Air-Piano/pulls) on the [GitHub repository](https://github.com/isranii/Air-Piano).

## License 📄

This project is open-source and available under the [MIT License](https://github.com/isranii/Air-Piano/blob/main/LICENSE).

## Acknowledgements

A sincere thank you to the developers and communities behind these remarkable open-source libraries that made this project possible:

* [OpenCV](https://opencv.org/): For its powerful computer vision functionalities.
* [cvzone](https://github.com/cvzone/cvzone): For simplifying hand tracking implementations.
* [Pygame](https://www.pygame.org/news): Specifically `pygame.midi` and `pygame.mixer`, for robust MIDI and audio capabilities.
* [NumPy](https://numpy.org/): For essential numerical operations.

## Credits / Contact

* **JAHNAVI ISRANI**
* **GitHub:** [https://github.com/isranii](https://github.com/isranii)
* **LinkedIn:** [https://www.linkedin.com/in/jahnaviisrani/](https://www.linkedin.com/in/jahnaviisrani/)
from heartrate import HeartRateManager, BeatFinder
from transcribe import transcribe_audio_with_speaker_diarization
import analyze
import pulsedb
import matching

import pigpio
import matplotlib
import matplotlib.pyplot as plt
import time
import traceback
import subprocess
import signal
from random import random

# Enable drawing IR LED data
SPO2_PLOT_EN = True
# Enable drawing red LED data
RED_PLOT_EN = False
# Enable drawing heartbeat detection data
BEAT_PLOT_EN = False

xs = [[] for i in range(HeartRateManager.NUM_SENSORS)]
cs = [0 for i in range(HeartRateManager.NUM_SENSORS)]
ys = [[[], [], []] for i in range(HeartRateManager.NUM_SENSORS)]
axs = [[None, None, None] for i in range(HeartRateManager.NUM_SENSORS)]
lines = [[None, None, None] for i in range(HeartRateManager.NUM_SENSORS)]
matplotlib.rcParams["toolbar"] = "None"
plt.style.use("dark_background")
(fig, a) = plt.subplots(1, HeartRateManager.NUM_SENSORS)
for i in range(HeartRateManager.NUM_SENSORS):
    axs[i][0] = a[i]
    axs[i][0].set_xlabel("time (s)")
    if SPO2_PLOT_EN:
        axs[i][0].set_ylabel("SpO2")
        (lines[i][0],) = axs[i][0].plot(xs[i], ys[i][0], color="#ffc0c0")
    if RED_PLOT_EN:
        axs[i][1] = axs[i][0].twinx()
        axs[i][1].set_ylabel("red")
        (lines[i][1],) = axs[i][1].plot(xs[i], ys[i][1], "-r")
    if BEAT_PLOT_EN:
        axs[i][2] = axs[i][0].twinx()
        axs[i][2].set_ylabel("beat")
        (lines[i][2],) = axs[i][2].plot(xs[i], ys[i][2], "-g")
fig.subplots_adjust(left=0.05, bottom=0.05, right=0.95, top=0.95, wspace=0.3)

beat_times = [[] for i in range(HeartRateManager.NUM_SENSORS)]
beat_lines = [[] for i in range(HeartRateManager.NUM_SENSORS)]
beat_finders = [BeatFinder() for i in range(HeartRateManager.NUM_SENSORS)]

def run():
    while True:
        try:
            hr = HeartRateManager()
        except pigpio.error as e:
            print(e)
            continue
        break

    # Set up audio recording files
    subprocess.run(["mkdir", "record"])
    filename_time = int(time.time())
    stereo_filename = f"record/stereo-{filename_time}.wav"
    print(f"Starting recording {stereo_filename}")
    # Start audio recording via SSH
    record_process = subprocess.Popen(f"exec ssh pi@pulse.local arecord -D dmic_sv -c2 -r 48000 -f S32_LE -t wav -V mono -v {stereo_filename}", stdout=subprocess.PIPE, shell=True)

    try:
        while True:
            for sensor_num in range(HeartRateManager.NUM_SENSORS):
                # Get data
                try:
                    (count, data1, data2) = hr.read_hr(sensor_num)
                except pigpio.error:
                    continue
                if count <= 0:
                    continue

                # Update lists
                for i in range(count):
                    xs[sensor_num].append(cs[sensor_num] / 50)
                    if SPO2_PLOT_EN:
                        ys[sensor_num][0].append(data2[i])
                    if RED_PLOT_EN:
                        ys[sensor_num][1].append(data1[i])

                    # Add heartbeat detection lines
                    if beat_finders[sensor_num].check_for_beat(data2[i]):
                        beat_times[sensor_num].append(cs[sensor_num] / 50)
                        if SPO2_PLOT_EN:
                            beat_lines[sensor_num].append(axs[sensor_num][0].axvline(cs[sensor_num] / 50, color="#ffffff"))
                    ys[sensor_num][2].append(beat_finders[sensor_num].get_cur())

                    cs[sensor_num] += 1

                # Prune old data
                if len(xs[sensor_num]) > 2 * 50:
                    xs[sensor_num] = xs[sensor_num][-2 * 50:]
                    if SPO2_PLOT_EN:
                        ys[sensor_num][0] = ys[sensor_num][0][-2 * 50:]
                    if RED_PLOT_EN:
                        ys[sensor_num][1] = ys[sensor_num][1][-2 * 50:]
                    if BEAT_PLOT_EN:
                        ys[sensor_num][2] = ys[sensor_num][2][-2 * 50:]
                # Prune old heartbeat lines
                for line in beat_lines[sensor_num]:
                    if line.get_xdata()[0] < cs[sensor_num] / 50 - 2:
                        line.remove()
                        beat_lines[sensor_num].remove(line)

                # Update plots
                if SPO2_PLOT_EN:
                    lines[sensor_num][0].set_data(xs[sensor_num], ys[sensor_num][0])
                if RED_PLOT_EN:
                    lines[sensor_num][1].set_data(xs[sensor_num], ys[sensor_num][1])
                if BEAT_PLOT_EN:
                    lines[sensor_num][2].set_data(xs[sensor_num], ys[sensor_num][2])

                for ax in axs[sensor_num]:
                    if ax is None:
                        continue
                    ax.relim()
                    ax.autoscale_view()
            plt.pause(0.01)
    except KeyboardInterrupt:
        # Stop audio recording
        print("\nSending SIGINT to ssh recording process")
        record_process.send_signal(signal.SIGINT)
        # Get a copy of audio recording via SCP
        print(f"Running scp for {stereo_filename}")
        subprocess.run(["scp", f"pi@pulse.local:{stereo_filename}", stereo_filename])
        # Convert audio recording to single channel audio
        mono_filename = f"record/mono-{filename_time}.wav"
        print(f"Running ffmpeg")
        subprocess.run(["ffmpeg", "-i", stereo_filename, "-ac", "1", mono_filename])

        for i in range(HeartRateManager.NUM_SENSORS):
            print(f"beat_times[{i}]:", beat_times[i])

        # Ask to perform analysis
        command = input("Command (enter for analyze, q for force quit): ")
        if command == "q":
            return

        # Get transcription of audio recording
        transcription_filename = f"record/{filename_time}.txt"
        print("Calling transcribe...")
        transcribe_audio_with_speaker_diarization(mono_filename, transcription_filename)

        # Get scores
        print("Analyzing...")
        for i in range(HeartRateManager.NUM_SENSORS):
            score = analyze.get_heartrate_score(beat_times[i])
            print(f"score {i}: {score}")
        pulsedb.addUserPair("Alicia", "Darren")
        id = pulsedb.getID()
        convo = open(transcription_filename, "r").read()
        result = analyze.ask_match(convo)
        convo_score = analyze.get_overall_conversation_score(result)
        heart_score = min(analyze.get_heartrate_score(beat_times[0]),
                          analyze.get_heartrate_score(beat_times[1]))
        pulsedb.updateScores(result.affection, result.vulnerability, result.kindness,
                             result.other, result.negative, result.explanation,
                             heart_score, convo_score, (convo_score + heart_score) / 2, id)
        print(f"Matching results: {matching.perform_matching()}")
    finally:
        print("Trying to clean up...", end="")
        while True:
            try:
                hr.stop()
            except:
                print(" failed:")
                traceback.print_exc()
                time.sleep(1)
                print("Trying again...", end="")
                continue
            break
        print(" done!")

if __name__ == "__main__":
    run()

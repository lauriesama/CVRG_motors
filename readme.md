# Motor Testing for Computer Vision and Robotics Group at Ualberta

Use requirements.txt.

```sudo pip install -r requirements.txt```

Use a .venv.

```python3 -m venv .venv```

```source .venv/bin/activate```

Use this command to callibrate your motor, target number may be different.

```python3 -m moteus.moteus_tool --target 1 --calibrate```

Running tview allows you to check/graph telemetry AND config, it is a diagnostic tool. Config will define motor performance. Tview will automatically find all motors assuming they are connected properly.

```tview```

Make sure to save your config using:

```conf write```

Use src/moteus/moteus_amp(s).py to test data, be sure to send appropriate voltages.

All data that I have done myself can be found in:

https://docs.google.com/spreadsheets/d/1M9c-frjZruW6cGknmP3VpxJ6dbNpB4GeUa8W1RtZVlY/edit?usp=sharing

Note the replication tab for more information about how to replicate the experiments.

This was made operating with the moteus python API found here. I HIGHLY recommend reading through the documentation. It contains a lot of information about the motor e.g. pinouts.

https://mjbots.github.io/moteus/reference/python/
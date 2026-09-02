import json
import sys
import time
import urllib.request

import websocket


CDP_URL = "http://localhost:9222/json"
ROBOT_URL = "https://sarthaki15.github.io/robot-python-bridge/"

MOVE_TIME = 1.5
STATE_UPDATE_INTERVAL = 0.25
MAX_STOPPED_READINGS = 3


# Store the latest robot information
state_info = {
    "state": {
        "x": 0,
        "z": 0,
        "rotationY": 0
    },
    "last_position": None,
    "last_update": 0,
    "stopped_count": 0
}


# Find the hosted robot tab in Chrome
def get_robot_tab():
    with urllib.request.urlopen(CDP_URL) as response:
        tabs = json.loads(response.read())

    for tab in tabs:
        if (
            tab.get("type") == "page"
            and tab.get("url", "").startswith(ROBOT_URL)
        ):
            return tab

    return None


# Process robot-state messages received from the webpage
def process_message(message):

    if message.get("method") != "Runtime.bindingCalled":
        return

    params = message.get("params", {})

    if params.get("name") != "robotStateFromPage":
        return

    try:
        state = json.loads(params["payload"])

        state_info["state"] = state

        position = (
            round(state["x"], 2),
            round(state["z"], 2),
            round(state["rotationY"], 2)
        )

        if position != state_info["last_position"]:

            state_info["last_position"] = position
            state_info["stopped_count"] = 0

            current_time = time.monotonic()

            if (
                current_time - state_info["last_update"]
                >= STATE_UPDATE_INTERVAL
            ):
                state_info["last_update"] = current_time
                print_state(state)

        else:

            state_info["stopped_count"] += 1

            if state_info["stopped_count"] <= MAX_STOPPED_READINGS:
                print_state(state)

    except (KeyError, TypeError, json.JSONDecodeError):
        pass


# Send a CDP command and wait for its response
def send_command(ws, command_id, method, params=None):

    message = {
        "id": command_id,
        "method": method
    }

    if params is not None:
        message["params"] = params

    ws.send(json.dumps(message))

    while True:

        response = json.loads(ws.recv())

        # CDP can send events while we are waiting
        if response.get("method") == "Runtime.bindingCalled":
            process_message(response)
            continue

        if response.get("id") == command_id:

            if "error" in response:
                raise RuntimeError(
                    f"CDP error in {method}: {response['error']}"
                )

            return response


# Print the current robot state
def print_state(state):
    print(
        f"    state  "
        f"x={state['x']:7.2f}  "
        f"z={state['z']:7.2f}  "
        f"rot={state['rotationY']:6.2f}"
    )


# Print movement/status information
def print_header(movement, action, key, status):

    print(
        f"\n[{movement}] "
        f"{action:<10} "
        f"key={key:<10} "
        f"status={status}"
    )

def dispatch_key(ws, command_id, event_type, key, key_code):

    return send_command(
        ws,
        command_id,
        "Input.dispatchKeyEvent",
        {
            "type": event_type,
            "key": key,
            "code": key,
            "windowsVirtualKeyCode": key_code
        }
    )

def move_robot(
    ws,
    command_id,
    movement_number,
    action,
    key,
    key_code,
    duration
):

    movement = f"MOVE {movement_number}"

    print_header(
        movement,
        action,
        key,
        "MOVING"
    )

    command_id += 1

    dispatch_key(
        ws,
        command_id,
        "keyDown",
        key,
        key_code
    )

    end_time = time.monotonic() + duration

    ws.settimeout(0.05)

    while time.monotonic() < end_time:

        try:
            message = json.loads(ws.recv())
            process_message(message)

        except websocket.WebSocketTimeoutException:
            pass

    ws.settimeout(None)

    command_id += 1

    dispatch_key(
        ws,
        command_id,
        "keyUp",
        key,
        key_code
    )

    print_header(
        movement,
        action,
        key,
        "STOPPED"
    )

    if state_info["state"]:
        print_state(state_info["state"])

    time.sleep(0.3)

    return command_id


def main():

    print("Python script started")

    # Find Chrome tab
    print("[1] Finding Chrome tab...")

    tab = get_robot_tab()

    if tab is None:
        print("Robot tab not found.")
        print("Make sure Chrome is running with remote debugging enabled.")
        sys.exit(1)

    print("[2] Robot tab found")

    # Connect to Chrome
    print("[3] Connecting to Chrome...")

    ws = websocket.create_connection(
        tab["webSocketDebuggerUrl"]
    )

    print("[4] Connected to Chrome!")

    command_id = 0

    try:

        # Enable Runtime events
        command_id += 1

        response = send_command(
            ws,
            command_id,
            "Runtime.enable"
        )

        print("[Runtime enabled]", response)

        # Test JavaScript execution
        command_id += 1

        response = send_command(
            ws,
            command_id,
            "Runtime.evaluate",
            {
                "expression": "document.title",
                "returnByValue": True
            }
        )

        print(
            "[JavaScript Test]",
            response["result"]["result"].get("value")
        )

        # Create a binding that JavaScript can call
        command_id += 1

        response = send_command(
            ws,
            command_id,
            "Runtime.addBinding",
            {
                "name": "robotStateFromPage"
            }
        )

        print("[Binding] Created")

        # Listen for robot-state messages from the webpage
        command_id += 1

        send_command(
            ws,
            command_id,
            "Runtime.evaluate",
            {
                "expression": """
                    window.addEventListener("message", (event) => {

                        if (event.source !== window) return;

                        if (event.data?.type !== "robot-state") return;

                        robotStateFromPage(
                            JSON.stringify(event.data)
                        );
                    });
                """
            }
        )

        print("[Listener] Robot state listener installed")

        # Give the webpage time to start sending state
        time.sleep(1.5)

        print_header(
            "STARTING",
            "Preparing",
            "-",
            "READY"
        )

        print_state(state_info["state"])

        time.sleep(1)

        # Movement 1
        command_id = move_robot(
            ws,
            command_id,
            1,
            "Forward",
            "ArrowUp",
            38,
            MOVE_TIME
        )

        # Movement 2
        command_id = move_robot(
            ws,
            command_id,
            2,
            "Turn Left",
            "ArrowLeft",
            37,
            MOVE_TIME
        )

        # Movement 3
        command_id = move_robot(
            ws,
            command_id,
            3,
            "Forward",
            "ArrowUp",
            38,
            MOVE_TIME
        )

        # Movement 4
        command_id = move_robot(
            ws,
            command_id,
            4,
            "Turn Right",
            "ArrowRight",
            39,
            MOVE_TIME
        )

        # Movement 5
        command_id = move_robot(
            ws,
            command_id,
            5,
            "Forward",
            "ArrowUp",
            38,
            MOVE_TIME
        )

        # Movement 6
        command_id = move_robot(
            ws,
            command_id,
            6,
            "Turn Left",
            "ArrowLeft",
            37,
            MOVE_TIME
        )

        # Start continuous monitoring
        print_header(
            "MONITOR",
            "Listening",
            "-",
            "ACTIVE"
        )

        print("Press keys in Chrome to move the robot.")
        print("Python will continue reading the robot state.")
        print("Press Ctrl+C to stop.")

        ws.settimeout(None)

        while True:

            message = json.loads(ws.recv())

            process_message(message)

    except KeyboardInterrupt:

        print("\nStopping Python script...")

    except websocket.WebSocketException as error:

        print(f"\nWebSocket error: {error}")

    except Exception as error:

        print(f"\nError: {error}")

    finally:

        ws.close()

        print("Connection closed.")


if __name__ == "__main__":
    main()
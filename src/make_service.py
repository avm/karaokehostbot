#!./venv/bin/python3
import os


def create_service(service_name, exec_start, working_directory):
    service_content = f"""
    [Unit]
    Description={service_name}
    After=network.target

    [Service]
    WorkingDirectory={working_directory}
    ExecStart={os.path.join(working_directory, exec_start)}
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=default.target
    """
    service_file_path = os.path.expanduser(
        f"~/.config/systemd/user/{service_name}.service"
    )
    os.makedirs(os.path.dirname(service_file_path), exist_ok=True)
    with open(service_file_path, "w") as service_file:
        service_file.write(service_content)
    print(f"Service file created at: {service_file_path}")
    return service_file_path


def enable_service(service_name):
    os.system("systemctl --user daemon-reload")
    os.system(f"systemctl --user enable {service_name}")
    os.system(f"systemctl --user start {service_name}")
    print(f"Service {service_name} enabled and started.")


if __name__ == "__main__":
    service_name = "kara0ke_party_bot"
    exec_start = "src/bot.py"
    working_directory = os.path.dirname(os.path.abspath(__file__))

    service_file_path = create_service(service_name, exec_start, working_directory)
    enable_service(service_name)

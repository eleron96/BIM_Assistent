
from rich.progress import Progress
from rich.console import Console
from rich.table import Table
from specklepy.api import operations
from specklepy.transports.server import ServerTransport

console = Console()


def print_discrepancy_rooms(discrepancy_rooms, commit_message):
    if discrepancy_rooms:
        console.print("The rooms have not been mapped!", style="bold red")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("№", style="dim")
        table.add_column("Rooms", style="dim")
        table.add_column("Name")
        table.add_column("Area in Revit")
        table.add_column("Rounded Area")
        table.add_column("Level")
        table.add_column("Room Number")

        for index, room in enumerate(discrepancy_rooms, start=1):
            table.add_row(
                str(index),
                f"{room['id']}",
                f"{room['name']}",
                f"{room['area']}",
                f"{room['rounded_area']}",
                f"{room['level_name']}",
                f"{room['room_number']}"
            )
        console.print(table)



def extract_check_area_discrepancy(obj):
    discrepancy_rooms = []

    # Check if the current object is a room
    if getattr(obj, 'category', None) == 'Помещения' and hasattr(obj, "parameters"):
        param_obj = obj.parameters
        area = None
        rounded_area = None
        other_params = {}
        level_name = None
        room_number = None

        for param_name, param_value in param_obj.__dict__.items():
            if hasattr(param_value, 'name'):
                normalized_param_name = param_value.name.lower()  # Normalize parameter name to lowercase
                if normalized_param_name == 'площадь':
                    area = param_value.value
                elif normalized_param_name == 'speech_площадь округлённая':
                    rounded_area = param_value.value
                elif normalized_param_name == 'уровень' and level_name is None:  # Check if level_name is not already set
                    level_name = param_value.value
                elif normalized_param_name == 'номер' and room_number is None:  # Check if room_number is not already set
                    room_number = param_value.value
                else:
                    other_params[param_value.name] = param_value.value

        if area is not None and rounded_area is not None and abs(area - rounded_area) > 0.4:
            discrepancy_info = {
                'id': obj.elementId,
                'name': obj.name,
                'area': area,
                'rounded_area': rounded_area,
                'level_name': level_name,
                'room_number': room_number
            }
            # Add other parameters to the discrepancy info
            discrepancy_info.update(other_params)
            discrepancy_rooms.append(discrepancy_info)

    # If we have 'elements', we need to check each element inside 'elements'
    for element in getattr(obj, 'elements', []):
        discrepancy_rooms.extend(extract_check_area_discrepancy(element))

    return discrepancy_rooms


def get_commits(branch_name=None):
    """Retrieve commits. If branch_name is provided, filter by branch."""
    limit = 100
    commits = client.commit.list(STREAM_ID, limit=limit)

    if branch_name:
        commits = [commit for commit in commits if
                   getattr(commit, 'branchName', '') == branch_name]

    return commits

def list_branches(print_to_console=True):
    """List available branches."""
    branches = client.branch.list(STREAM_ID)
    if print_to_console:
        for idx, branch in enumerate(branches):
            print(f"[{idx + 1}] {branch.name}")
    return [branch.name for branch in branches]

def check_area_discrepancy():
    branches = list_branches(print_to_console=False)
    discrepancy_reports = []

    with Progress() as progress:
        task1 = progress.add_task("[cyan]Processing branches...",
                                  total=len(branches))

        for branch in branches:
            if branch.lower() == "main":
                progress.advance(task1)
                continue

            commits = get_commits(branch_name=branch)
            if not commits:
                progress.advance(task1)
                continue

            commits.sort(key=lambda x: getattr(x, 'createdAt', None),
                         reverse=True)
            last_commit = commits[0]

            try:
                # Теперь передаем stream_id вместе с last_commit и client
                transport = ServerTransport(client=client, stream_id=STREAM_ID)
                res = operations.receive(last_commit.referencedObject,
                                         transport)
                room_section = extract_check_area_discrepancy(res)
                discrepancy_reports.append((branch,
                                            getattr(last_commit, 'message',
                                                    None), room_section))
            except Exception as e:
                discrepancy_reports.append(
                    (branch, "Corpus section short: " + str(e), None))

            progress.advance(task1)

    # После обработки всех веток, выводим собранную информацию
    for branch, commit_message, rooms in discrepancy_reports:
        console.print(f"Checking branch: [bold green]{branch}[/bold green]")
        console.print(f"Commit Message: [bold]{commit_message}[/bold]",
                      style="bold green")
        if rooms:
            print_discrepancy_rooms(rooms, commit_message)
        else:
            console.print("The rooms have been mapped", style="bold green")
        console.print("-" * 40)
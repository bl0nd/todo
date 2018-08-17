#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    todo.py
    ~~~~~~~

    A manager for TODO lists.

NOTES:
    [ ] List colors

            for i in range(0, curses.COLORS):
                curses.init_pair(i+1, i, -1)  # -1 is transparent
            for i in range(0, 255):
                win.addstr(str(i), curses.color_pair(i))
            win.addstr(' ' * width)
            win.addstr(' ' * (width-65))
"""
import os
import sys
import json
import argparse
import curses
import time
import textwrap
from pathlib import Path
from curses import wrapper, newwin


"""
[+++++++++++++++++++++++++++++++++++++++++++++]
                   Parser
[+++++++++++++++++++++++++++++++++++++++++++++]
"""

class ArgumentParser(argparse.ArgumentParser):
    """Overriding class for custom help/usage message."""
#     @staticmethod
#     def error(self):
#         """Print usage message and the error that occured."""
#         print(self)
#         sys.exit()
#         print('''\n\
# Usage:
#   todo.py [-h] [project] [section option] [section] [task option]

# Error: ''', end='')
#         sys.exit(f'{sys.exc_info()}\n')

    def print_help(self):
        """Print custom help menu."""
        print('''\
usage: python todo.py [--help] [<mode>] [<label> <args>]

Modes:
   normal      [PROJECT] [SECTION]           View or modify existing projects
   creation    create PROJECT                Create a new project
   deletion    delete PROJECT                Delete a project
   archive     archive [PROJECT] [SECTION]   Archive completed tasks

Normal mode options:
  tasks
    -a LABEL   Add a task.
    -d LABEL   Delete a task.
    -c LABEL   Mark a task as complete.
    -u LABEL   Mark a task as incomplete.

  sections
    -sa LABEL  Add a section.
    -sd LABEL  Delete a section.
    -sc LABEL  Mark a section as complete.
    -su LABEL  Mark a section as incomplete.
''')


def create_parser(menu, args, todo_file):
    """Create a command-line parser.

    For a custom usage menu, uses an overridden `MyParser` instance.

    Since I can't figure out how to make option "--create" mutually exclusive
    with positional arguments "project" and "section", without making the 2
    latter options exclusive with the task and section options, the ugly
    `create` variable will suffice in telling class `Todo` if we want to
    view/modify a project or make one.

    I couldn't use a subparser since that would break when a project named
    "create" is made.

    Args:
        None

    Returns:
        A Namespace object containing the command-line flags and their state.
        A boolean indicating if the user is making a project.
    """
    parser = ArgumentParser()
    sp = parser.add_subparsers()

    if not args:
        parser.set_defaults(project=None, section=None, create=False)
        try:
            Todo(menu, parser.parse_args(), todo_file)
        except curses.error as e:
            sys.exit('Error: Terminal window is not large enough.')
        sys.exit(0)

    with open(todo_file) as f:
        data = json.load(f)
    existing_projects = [project for project in data.keys()]

    if args[0] not in existing_projects + ['create', 'delete', 'archive', '-h', '--help']:
        sys.exit(f'Project "{args[0]}" does not exist.')

    # Normal Mode
    sp_normal = sp.add_parser('',
        aliases=[*existing_projects],
        help='View or modify existing projects')
    sp_normal.set_defaults(project=args[0], create=False, delete=False, archive=False)
    sp_normal.add_argument('-a', action='store', dest='add')

    mutual = sp_normal.add_mutually_exclusive_group()
    mutual.add_argument('section', action='store', nargs='?')
    mutual.add_argument('-d', type=int, action='store', dest='task_delete')
    mutual.add_argument('-c', action='store', dest='check')
    mutual.add_argument('-u', action='store', dest='uncheck')
    mutual.add_argument('-sa', action='store', dest='section_add')
    mutual.add_argument('-sd', action='store', dest='section_delete')
    mutual.add_argument('-sc', action='store', dest='section_check')

    # Create Mode
    sp_create = sp.add_parser('create',
        description='Creates a new project.',
        help='Create a new project',
        add_help=False)
    sp_create.set_defaults(create=True, delete=False, archive=False, project=None, section=None)
    sp_create.add_argument('project', type=str, action='store', help='Name of project')

    # Delete Mode
    sp_delete = sp.add_parser('delete',
        description='Deletes an existing project.',
        help='Delete a project',
        add_help=False)
    sp_delete.set_defaults(delete=True, create=False, archive=False, project=None, section=None)
    sp_delete.add_argument('project', action='store', help='Name of project')

    # Archive
    sp_archive = sp.add_parser('archive',
        description='Deletes an existing project.',
        help='Delete a project',
        add_help=False)
    sp_archive.set_defaults(archive=True, create=False, delete=False, project=None, section=None)
    sp_archive.add_argument('project', nargs='?', action='store', help='Name of project')
    sp_archive.add_argument('section', nargs='?', action='store', help='Name of section')

    return parser.parse_args()

"""
[+++++++++++++++++++++++++++++++++++++++++++++]
                   Todo
[+++++++++++++++++++++++++++++++++++++++++++++]
"""

def update_check(project, section=None, proj_sections=None):
    """Archive helper function."""
    if section:
        for sect in proj_sections:
            if section == sect['name']:
                sect_tasks = sect['tasks']
        checked = set(project['check']) & set(sect_tasks)
        if not checked:
            sys.exit(f'No completed tasks in section "{section}".')  # Need to specify project name
        return checked, sect_tasks
    else:
        checked = [task_num for task_num in project.get('check')]
        if not checked:
            sys.exit(f'No completed tasks.')
        return checked

def delete_tasks(project, checked, section=None, proj_tasks=None):
    """Archive helper function."""
    old_tasks = project['tasks']
    new_tasks = {}
    tasks = proj_tasks.items() if section else project.get('tasks').items()

    for task_num, task in project.get('tasks').items():
        if int(task_num) not in checked:
            new_tasks[str(len(new_tasks) + 1)] = task
    return old_tasks, new_tasks

def update_sections(project, sections, old_tasks, new_tasks, checked):
    """Archive helper function."""
    new_tnames = list(new_tasks.values())
    all_sect_tasks = {}

    for sect in sections:
        sect_tasks = list(set(sect['tasks']) - checked)
        for i, task_num in enumerate(sect_tasks):
            old_tname = old_tasks.get(str(task_num))
            sect_tasks[i] = new_tnames.index(old_tname) + 1
        all_sect_tasks[sect['name']] = (sorted(sect_tasks))
    return all_sect_tasks, new_tnames

class Todo(object):
    """Class for managing TODO list states.

    Args:
        menu:      (Menu)       Instance of our curses wrapped drawing class, `Menu`.
        args:      (Namespace)  Contains command-line flags and their states.
        todo_file: (String)     The JSON file to read from and write to (the option
                                    to specify exists so that when testing, a test
                                    JSON file can be used instead).

    Attributes:
        menu:          (Menu)    arg: menu
        todo_file:     (String)  arg: todo_file
        data:          (dict)    JSON file containing the TODO list.
        iter_data:     (list)    List representation of `data` (for indexing).
        project:       (String)  Name of project to view or modify.
        section:       (String)  Name of section to create, view, or modify.
        proj_sections: (list)    Contains dicts with section names as keys and
                                    section tasks as values.
        proj_tasks:    (dict)    Task number as keys, task label as values.
    """
    def __init__(self, menu, args=None, todo_file=None):
        """Constructor. See class docstring."""
        self.args=args
        self.menu = menu
        self.todo_file = todo_file

        with open(self.todo_file) as f:
            self.data = json.load(f)
            if not self.data and not args.create:
                sys.exit('No projects exist.')

        self.iter_data = list(self.data.items())
        self.project = args.project
        self.section = args.section

        if len(sys.argv) == 1:
            self.show()
        elif args.project or args.section:
            self.proj_sections, self.proj_tasks = self.find_project()

    # >>> General functions

    def write(self):
        """Write changes to the TODO list's JSON file.

        Normally, it will be .todo. However, when testing, it'll use the test
            file .test_todo.
        """
        with open(self.todo_file, 'w') as f:
            json.dump(self.data, f)

    def find_project(self):
        """Return the sections and tasks of a project.

        Args:
            None

        Returns:
            A tuple made of the specified project's sections in a list and tasks
            in a dict.
        """
        sections = []
        tasks = []
        for i, project in enumerate(self.data.keys()):
            if self.project == project:
                sections.append(list(self.iter_data[i][1]['sections']))
                tasks.append(list(self.iter_data[i][1]['tasks'].items()))

        # section check is in main since it needs proj_sections
        if not tasks:
            sys.exit(f'project "{self.project}" does not exist.')
        else:
            return (*sections, dict(*tasks))

    def show(self):
        """Display TODO list.

        Has 3 sections based on the arguments passed to todo:

            a)   $ todo project section
            b)   $ todo project
            c)   $ todo

        a) displays the project specified, the section specified and its tasks.
        b) displays the project specified, all sections within it, and all
             tasks.
        c) displays all projects, their sections, and all of their tasks.

        Tasks belonging to a section will be excluded from the general task
            output area since they're already included in the section task area.

        Args:
            None

        Returns:
            None
        """
        if self.project or self.section:
            wrapper(self.menu.draw_prjsect,
                self.data,
                self.proj_sections,
                self.proj_tasks,
                self.project,
                self.section)
        else:
            wrapper(self.menu.draw_all, self.data, self.iter_data)

    def delete(self):
        """Delete a project."""
        try:
            self.data.pop(self.project)
        except KeyError as e:
            sys.exit(f'Project "{self.project}" does not exist.')
        self.write()

    def create(self):
        """Create a new project."""
        blacklist = ['create', 'delete', 'init']
        existing_projects = [project for project in self.data.keys()]

        if not self.project.isalnum():
            sys.exit('Invalid project name.')
        elif self.project in blacklist:
            sys.exit('Error: Restricted project name.')
        elif self.project in existing_projects:
            sys.exit(f'Project "{self.project}" already exists.')
        elif len(self.project) > 45:
            sys.exit('Project name is too long.')

        self.data[self.project] = {"sections": [], "tasks": {}, "check": []}
        self.write()

    def archive(self):
        """Delete completed tasks for sections.

        Bug:
            When assigning new section tasks to sect['tasks'], we indirectly
              modify self.data since we're iterating over self.proj_sections.
              Because we didn't iterate over self.proj_tasks, we just assigned
              new_tasks to it, that didn't affect self.data.
              So we can either call it a feature and not include:

                    project['sections'] = self.proj_sections

              or we can fix update_sections() so that it returns an updated
              copy of self.proj_sections.

              Or we can just not change self.proj_sections/tasks since we aren't
              going to call self.show().
        """
        if self.section:
            # Update check list
            project = self.data[self.project]
            checked, sect_tasks = update_check(project, self.section, self.proj_sections)
            project['check'] = list(set(project['check']) - set(sect_tasks))

            # Delete tasks
            old_tasks, new_tasks = delete_tasks(project, checked, self.section, self.proj_tasks)
            project['tasks'] = new_tasks


            # Update sections
            all_sect_tasks, new_tnames = update_sections(project, self.proj_sections, old_tasks, new_tasks, checked)
            for sect in self.proj_sections:
                if sect['name'] in all_sect_tasks.keys():
                    sect['tasks'] = all_sect_tasks.get(sect['name'])

            # Update check list
            for i, task in enumerate(project['check']):
                old_tnames = old_tasks.get(str(task))
                project['check'][i] = new_tnames.index(old_tnames) + 1
        elif self.project:
            self.archive_projects(self.data[self.project])
        else:
            for name, project in self.data.items():
                self.archive_projects(project)

        self.write()
        # self.show()
        print(self.data)

    def archive_projects(self, project):
        """Delete completed tasks for projects."""
        # Empty check list
        checked = set(update_check(project))
        project['check'] = []

        # Delete tasks
        old_tasks, new_tasks = delete_tasks(project, checked)
        project['tasks'] = new_tasks

        # Update sections
        all_sect_tasks, new_tnames = update_sections(project, project['sections'], old_tasks, new_tasks, checked)
        for sect in project['sections']:
            if sect['name'] in all_sect_tasks.keys():
                sect['tasks'] = all_sect_tasks.get(sect['name'])



    # >>> Task functions

    def add(self):
        """Add a task to a project.

        If a section is specified, the task's number will be added to the
          corresponding section's key `task` to indicate it's a section task.
        """
        label = self.args.add

        if label in self.proj_tasks.values():
            sys.exit(f'Task "{label}" already exists in project "{self.project}"')

        # add task
        self.proj_tasks[len(self.proj_tasks) + 1] = label
        self.data[self.project]['tasks'] = self.proj_tasks
        self.write()

        # update section if a section task is added
        if self.section:
            sections = self.data[self.project]['sections']
            for section in self.data[self.project]['sections']:
                if self.section == section.get('name'):
                    section['tasks'].append(len(self.proj_tasks))
                    self.write()

    def task_delete(self):
        """Delete a task from a project.

        If a section is specified, the task's position number will be removed
          from the section's `task` key.
        """
        position = self.args.task_delete
        if position <= len(self.proj_tasks):
            # delete task at `position`
            for project, info in self.iter_data:
                if self.project == project:
                    self.data[project]['tasks'].pop(str(position))

            # update section pointers
            section_tasks = []
            for section in self.proj_sections:
                section_tasks.append(section.get('tasks'))

            for sect_tasks in section_tasks:
                if position in sect_tasks:
                    sect_tasks.remove(position)
                for i,v in enumerate(sect_tasks):
                    if v > position:
                        sect_tasks[i] = v - 1

            # update check list
            if position in self.data[self.project]['check']:
                self.data[self.project]['check'].remove(position)

            for i,v in enumerate(self.data[self.project]['check']):
                if v > position:
                    self.data[self.project]['check'][i] = v - 1

            # update task list indices
            updated_tasks = self.data[self.project]['tasks'].items()
            new_tasks = {}
            for old_index, task in updated_tasks:
                if position <= int(old_index):
                    new_index = str(int(old_index) - 1)
                    new_tasks[new_index] = task
                else:
                    new_tasks[old_index] = task

            # dump to file
            self.data[self.project]['tasks'] = new_tasks
            self.write()
        else:
            sys.exit(f'Project "{self.project}" has no task #{position}.')

    def check(self):
        """Mark a task as checked."""
        label = self.args.check
        check_list = self.data[self.project]['check']
        task_list = list(self.proj_tasks.values())
        if label in task_list:
            for task_num, task in self.proj_tasks.items():
                if label == task:
                    if int(task_num) not in check_list:
                        check_list.append(int(task_num))
                        self.write()
                    else:
                        sys.exit(f'Task "{label}" is already checked.')
        else:
            sys.exit(f'Task "{label}" does not exist.')

    def uncheck(self):
        """Unmark a checked task."""
        label = self.args.uncheck
        check_list = self.data[self.project]['check']
        task_list = list(self.proj_tasks.values())
        if label in task_list:
            for task_num, task in self.proj_tasks.items():
                if label == task:
                    if int(task_num) in check_list:
                        check_list.remove(int(task_num))
                        self.write()
                    else:
                        sys.exit(f'Task "{label}" is not checked.')
        else:
            sys.exit(f'Task "{label}" does not exist.')

    # >>> Section functions


    def section_add(self):
        """Add a section."""
        label = self.args.section_add
        if label in [sect.get('name') for sect in self.proj_sections]:
            sys.exit(f'Section "{label}" already exists in project "{self.project}".')

        sections = self.data[self.project]['sections']
        sections.append({"name": label, "tasks": []})
        self.write()

    def section_delete(self):
        """Delete a section."""
        label = self.args.section_delete
        if label not in [sect.get('name') for sect in self.proj_sections]:
            sys.exit(f'Section "{label}" does not exist in project "{self.project}".')

        sections = self.data[self.project]['sections']
        tasks = self.data[self.project]['tasks']

        # delete section and tasks marked as a section task
        for i, sect in enumerate(sections):
            if label == sect.get('name'):
                to_remove = sect.get('tasks')
                del sections[i]
                for task in to_remove:
                    tasks.pop(str(task))

        # update task indices
        for i,v in enumerate(tasks.keys()):
            if len(tasks.keys()) > i:
                tasks[str(i+1)] = tasks.pop(v)

        self.write()



"""
[+++++++++++++++++++++++++++++++++++++++++++++]
                 Curses
[+++++++++++++++++++++++++++++++++++++++++++++]
"""

class Menu(object):
    """Manager for curses drawings.

    Args:
        stdscr: (Window) Represents the entire screen.

    Attributes:
        begin_x: (int)
        begin_y: (int)
        height: (int)
        width: (int)
        win: ()
        colors: (dict)
        excl: (String)
        color: (String)
        quote: (String)
        hash: (String)
        check: (String)
        blank: (String)
        section_tasks: (list)
    """
    def __init__(self, stdscr):
        """Constructor. See class docstring."""
        # Window attributes
        self.begin_x = 1
        self.begin_y = 2
        self.height = curses.LINES
        self.width = curses.COLS
        self.win = newwin(self.height, self.width, self.begin_y, self.begin_x)

        # Colors
        self.init_colors()
        self.colors = {"r": (1, 2, 3, 4, 5, 6, 7, 8),
                       "g": (9, 10, 11, 12, 13, 14, 15, 16),
                       "b": (17, 18, 19, 20, 21, 22, 23, 24)}

        # Prefixes
        self.excl  = ' !!! '
        self.color = '{} '
        self.quote = '"'
        self.hash  = '     # '
        self.check = '     ✓ '
        self.blank = '{}\n'.format(' ' * 56)

        # Drawing necessities
        self.section_tasks = []

    def init_colors(self):
        """Initialize custom curses color pairs.

        Color pair mapping:

            Let x = {1, 9, 17},

                x:        ! and double quotes ("")
                x + 1:    Color letter (e.g., r, g, b)
                x + 2:    Project name
                x + 3:    Body background
                x + 4:    Task
                x + 5:    Hash
                x + 6:    Section name
                x + 7:    Checkmark

        Args:
            None

        Returns:
            None
        """
        curses.use_default_colors()

        # Red
        curses.init_pair(1, 203, 167)
        curses.init_pair(2, 210, 167)
        curses.init_pair(3, 253, 167)
        curses.init_pair(4, -1, 131)
        curses.init_pair(5, 253, 131)
        curses.init_pair(6, 203, 131)
        curses.init_pair(7, 210, 131)
        curses.init_pair(8, 46, 131)

        # Green
        curses.init_pair(9, 76, 71)
        curses.init_pair(10, 119, 71)
        curses.init_pair(11, 253, 71)
        curses.init_pair(12, -1, 65)
        curses.init_pair(13, 253, 65)
        curses.init_pair(14, 76, 65)
        curses.init_pair(15, 210, 65)
        curses.init_pair(16, 46, 65)

        # Blue
        curses.init_pair(17, 75, 69)
        curses.init_pair(18, 45, 69)
        curses.init_pair(19, 253, 69)
        curses.init_pair(20, -1, 67)
        curses.init_pair(21, 253, 67)
        curses.init_pair(22, 75, 67)
        curses.init_pair(23, 210, 67)
        curses.init_pair(24, 46, 67)

    def draw_banner(self, stdscr, clrs, proj_color, proj_name, end_banner):
        """Draw the TODO project's banner.

        The banner includes the "!!!"  prefix, the project's color label (e.g.,
          r, g, b), and and project's name.

        Args:
            stdscr: (Window) Represents the entire screen.
            clrs:   (tuple) 8 sequential numbers that corresponds to the proper
                curses color pair.
            proj_color: (String) Color of project (e.g., r, g, b).
            proj_name: (String) Name of project.
            end_banner: (String) A line full of spaces to finish the banner.

        Returns:
            None
        """
        end_banner = '"{}\n'.format(' ' * (56 - len(proj_name) - 9))
        self.win.addstr(self.excl, curses.color_pair(clrs[0]))
        self.win.addstr(self.color.format(proj_color), curses.A_BOLD | curses.color_pair(clrs[1]))
        self.win.addstr(self.quote, curses.color_pair(clrs[0]))
        self.win.addstr(proj_name, curses.A_BOLD | curses.color_pair(clrs[2]))
        self.win.addstr(end_banner, curses.color_pair(clrs[0]))

    def draw_tasks(self, stdscr, task_num, tname, check_list, clrs, section=False):
        """Draw regular and section tasks.

        The only difference in drawing regular and section tasks is that section
            tasks are indented 2 more spaces than regular ones.

        Args:
            stdscr: (Window) Represents the entire screen.
            task_num: (int) The current task's index.
            check_list: (list) Contains task indices that are marked as checked.
            tname: (String) Name of task.
            clrs: (tuple) 8 sequential numbers that corresponds to the proper
                curses color pair.
            section: (boolean) Indicates whether the current task is a regular
                or section task.
        """
        if section:
            prefix = '  '
            suffix = '{}\n'.format(' ' * (56 - len(tname) - 9))
            length = 42
        else:
            prefix = ''
            suffix = '{}\n'.format(' ' * (56 - len(tname) - 7))
            length = 44

        if len(tname) > length:
            for i, substr in enumerate(textwrap.wrap(tname, width=length)):
                if section:
                    suffix = '{}\n'.format(' ' * (56 - len(substr) - 9))
                else:
                    suffix = '{}\n'.format(' ' * (56 - len(substr) - 7))

                if i == 0:
                    if task_num in check_list:
                        self.win.addstr(f'{prefix}{self.check}', curses.color_pair(clrs[7]))
                        self.win.addstr(f'{substr}{suffix}', curses.color_pair(clrs[4]))
                    else:
                        self.win.addstr(f'{prefix}     □ {substr}{suffix}', curses.color_pair(clrs[4]))
                else:
                    self.win.addstr(f'{prefix}       {substr}{suffix}', curses.color_pair(clrs[4]))
        else:
            if task_num in check_list:
                self.win.addstr(f'{prefix}{self.check}', curses.color_pair(clrs[7]))
                self.win.addstr(f'{tname}{suffix}', curses.color_pair(clrs[4]))
            else:
                self.win.addstr(f'{prefix}     □ {tname}{suffix}', curses.color_pair(clrs[4]))

    def draw_sections(self, stdscr, check_list, clrs, proj_tasks, sect):
        """Draw sections.

        Args:
            stdscr: (Window) Represents the entire screen.
            check_list: (list) Task indices for tasks marked as checked.
            clrs: (tuple) 8 sequential numbers that corresponds to the proper
                curses color pair.
            proj_tasks: (dict) All tasks and their index for the specified
                project.
            sect: (dict) Name and tasks for the current section.

        Returns:
            None
        """
        # Section
        end_sec = '{}\n'.format(' ' * (56 - len(sect.get('name')) - 7))
        self.win.addstr(self.hash, curses.color_pair(clrs[5]))
        self.win.addstr(f'{sect.get("name")}{end_sec}', curses.color_pair(clrs[6]))

        # Section tasks
        task_nums = sect.get('tasks')
        for task_num in task_nums:
            tname = proj_tasks.get(str(task_num))
            wrapper(self.draw_tasks, task_num, tname, check_list, clrs, section=True)
        self.win.addstr(self.blank, curses.color_pair(clrs[3]))

    def draw_prjsect(self, stdscr, projects, proj_sections, proj_tasks, project, section):
        """Draw a specific project.

        If a section is specified, draw only the project, the specified section,
            and its tasks.

        Args:
            stdscr: (Window) Represents the entire screen.
            proj_sections: (list) All sections in dictionaries (which contains
                the section name and its tasks.)
            proj_tasks: (dict) All tasks and their index for the specified
                project.
            project: (String) Name of the specified project.
            section: (String) Name of the specified section.

        Returns:
            None
        """
        section_tasks = {str(num) for sect in proj_sections for num in sect.get('tasks')}
        check_list = projects.get(project).get('check')
        end_banner = '"{}\n'.format(' ' * (56 - len(project) - 9))

        # Colors
        for i, prj in enumerate(projects):
            if prj == project:
                proj_color = list(self.colors.keys())[i % 3]
        clrs = self.colors.get(proj_color)

        # Banner
        wrapper(self.draw_banner, clrs, proj_color, project, end_banner)

        # Pre-body
        self.win.addstr(self.blank * 2, curses.color_pair(clrs[3]))

        # Body
        if section:
            # sections and section tasks
            for sect in proj_sections:
                if section == sect.get('name'):
                    wrapper(self.draw_sections, check_list, clrs, proj_tasks, sect)

            # end lines
            for i in range(2):
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))
        elif project:
            # sections and section tasks
            for sect in proj_sections:
                wrapper(self.draw_sections, check_list, clrs, proj_tasks, sect)

            # tasks
            if proj_sections:
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))
            for task_num, tname in proj_tasks.items():
                if task_num not in section_tasks:
                    wrapper(self.draw_tasks, int(task_num), tname, check_list, clrs, section=False)

            # end lines
            if set(proj_tasks.keys()) - section_tasks:
                body_end = 3
            else:
                body_end = 1
            for i in range(body_end):
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))

        # Block
        self.win.getch()

    def draw_all(self, stdscr, projects, iter_projects):
        """Draw all projects, sections, and tasks.

        Args:
            stdscr: (Window) Represents the entire screen.
            projects: (dict) All projects (as keys) and their sections and
                tasks (as values).
            iter_projects: (list) All projects (as list[i][0]) and their
                sections and tasks (list[i][1]).

        Returns:
            None
        """
        for i, proj in enumerate(projects):
            proj_sections = iter_projects[i][1]['sections']
            proj_tasks = iter_projects[i][1]['tasks']
            proj_name = iter_projects[i][0]
            section_tasks = {str(num) for sect in proj_sections for num in sect.get('tasks')}
            check_list = projects.get(proj).get('check')
            proj_color = list(self.colors.keys())[i % 3]
            clrs = self.colors.get(proj_color)

            # Banner
            end_banner = '"{}\n'.format(' ' * (56 - len(proj_name) - 9))
            wrapper(self.draw_banner, clrs, proj_color, proj_name, end_banner)

            # Pre-body
            self.win.addstr(self.blank * 2, curses.color_pair(clrs[3]))

            # Body
            for sect in proj_sections:
                # section
                wrapper(self.draw_sections, check_list, clrs, proj_tasks, sect)

            # tasks
            if proj_sections:
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))
            for task_num, tname in proj_tasks.items():
                if task_num not in section_tasks:
                    wrapper(self.draw_tasks, int(task_num), tname, check_list, clrs, section=False)

            # end
            if set(proj_tasks.keys()) - section_tasks:
                body_end = 3
            else:
                body_end = 1
            for i in range(body_end):
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))

            self.win.addstr(' ' * self.width)
            self.win.addstr(' ' * self.width)

        # Block
        self.win.getch()

"""
[+++++++++++++++++++++++++++++++++++++++++++++]
                   Main
[+++++++++++++++++++++++++++++++++++++++++++++]
"""
def init(args):
    if args and args[0] == 'init':
            if not Path('.todo').exists():
                Path('.todo').write_text('{}')
                sys.exit(0)
            else:
                sys.exit('Error: Already a todo respository: .todo')
    elif not Path('.todo').exists():
        sys.exit('Error: Not a todo repository: .todo.')

def main(args=sys.argv[1:], todo_file=None):
    """Main program, used when run as a script."""
    init(args)  # todo configuration file checks
    menu = wrapper(Menu)
    parser = create_parser(menu, args, todo_file)
    # print(parser)
    todo = Todo(menu, parser, todo_file)

    if parser.section:
        section_tasks = []
        for section in todo.proj_sections:
            section_tasks.append(section.get('name'))
        if parser.section not in section_tasks:
            sys.exit(f'section "{parser.section}" of project '
                     f'"{parser.project}" does not exist.')

    if parser.create:
        todo.create()
    elif parser.delete:
        todo.delete()
    elif parser.archive:
        todo.archive()
    else:
        if parser.add:
            todo.add()
        elif parser.task_delete:
            todo.task_delete()
        elif parser.check:
            todo.check()
        elif parser.uncheck:
            todo.uncheck()
        elif parser.section_add:
            todo.section_add()
        elif parser.section_delete:
            todo.section_delete()
        elif parser.project or (parser.project and parser.section):
            try:
                todo.show()
            except:
                sys.exit('Error: Terminal window is not large enough.')


if __name__ == '__main__':
    full_path = os.path.realpath(__file__)
    tf = f'{os.path.dirname(full_path)}/.todo'
    main(todo_file=tf)

#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    todo.py
    ~~~~~~~

    A manager for TODO lists.

NOTES:
    [ ] List colors

            def test(stdscr):
                curses.start_color()
                curses.use_default_colors()
                begin_x = 1
                begin_y = 2
                height = curses.LINES
                width = curses.COLS
                win = newwin(height, width, begin_y, begin_x)

                for i in range(0, curses.COLORS):
                    curses.init_pair(i+1, i, -1)  # -1 is transparent
                for i in range(0, 255):
                    win.addstr(str(i), curses.color_pair(i))

                curses.init_pair(1, 171, 141)  # !, ""
                curses.init_pair(2, 219, 141)  # r,g,b,v
                curses.init_pair(3, 254, 141)  # Project
                curses.init_pair(4, 254, 97)   # Task
                win.addstr(' ' * width)
                win.addstr(' ' * (width-65))

                win.addstr(' !!!', curses.color_pair(1))
                win.addstr(' v', curses.color_pair(2))
                win.addstr(' "', curses.color_pair(1))
                win.addstr('O', curses.color_pair(3))
                win.addstr('"', curses.color_pair(1))
                win.addstr(' ' * (width-75), curses.color_pair(1))
                win.addstr(' ' * 65)
                win.addstr('bbbbb', curses.color_pair(4))
                win.addstr(' ' * (width-70), curses.color_pair(4))
                win.addstr(' ' * (width-53))
                win.addstr(' ' * (width-70), curses.color_pair(4))
                win.addstr('hi')
                win.addstr(' ' * (width-70), curses.color_pair(4))
                win.addstr(' ' * 65)
                win.addstr(' ' * (width-70), curses.color_pair(4))
                win.addstr(' ' * 65)
                win.addstr(' ' * (width-70), curses.color_pair(4))

                win.getch()
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
    def error(self, message):
        """Custom error messages.
        
        This is to avoid an ugly error message for something like `$ todo aaaaa`
        when "aaaaa" isn't a project name.
        """
        error_msg_left = message.split(':')[0]
        error_msg_right = message.split(':')[1]

        # Check for nonexistent project names (normal)
        if error_msg_left == 'invalid choice':
            sys.exit(f'project "{sys.argv[1]}" does not exist.')

        # Check for missing arguments (normal, create, delete)
        elif (error_msg_left == 'the following arguments are required' or
              error_msg_right == ' expected one argument'):
            sys.exit(message) 
        
        # Check for extra arguments (normal, create, delete, archive)
        elif error_msg_left == 'unrecognized arguments':
            extra_args = error_msg_right.split(' ')[1:]
            suffix = '' if len(extra_args) == 1 else 's'
            if len(extra_args) == 1:
                extra_args = "'{}'".format(extra_args[0])
            else:
                extra_args = "'{}'".format("', '".join(extra_args))
            sys.exit(f'error: unrecognized argument{suffix} {extra_args}.')
        
        # Check for too many arguments (it'll think you're providing a section)
        elif error_msg_left == 'argument section':
            sys.exit('error: too many arguments')
        else:
            sys.exit(f'UNKNOWN ERROR: {message}')

    def print_help(self):
        """Print custom help menu."""
        print('''\
usage: python todo.py [--help] [<mode>] [<label> <args>]

Modes:
   normal      [PROJECT [SECTION]]           View or modify existing projects
   creation    create PROJECT                Create a new project
   deletion    delete PROJECT                Delete a project
   archive     archive [PROJECT [SECTION]]   Archive completed tasks

Normal mode options:
  general
    -r LABEL                        Rename a project or section.
  tasks
    -a LABEL                        Add a task.
    -d LABEL                        Delete a task.
    -c LABEL                        Mark a task as complete.
    -u LABEL                        Mark a task as incomplete.
    -mp LABEL PROJECT               Move a task to a different project.
    -ms LABEL PROJECT SECTION       Move a task to a different section.

  sections
    -sa LABEL  Add a section.
    -sd LABEL  Delete a section.
''')
#     -sc LABEL  Mark a section as complete.
#     -su LABEL  Mark a section as incomplete.

def create_parser(menu, todo_file):
    """Create a command-line parser.

    For a custom usage menu, uses an overridden `ArgumentParser` instance.

    Args:
        todo_file: (String) Absolute path of .todo.

    Returns:
        A Namespace object containing the command-line flags and their state.
    """
    parser = ArgumentParser()
    sp = parser.add_subparsers()

    # If in normal mode and no project/section specified, display all projects
    if len(sys.argv) == 1:
        parser.set_defaults(project=None, section=None)
        try:
            Todo(menu, parser.parse_args(), todo_file)
        except curses.error as e:
            sys.exit('error: terminal window is not large enough.')
        sys.exit(0)

    # Make sure init
    with open(todo_file) as f:
        data = json.load(f)
    existing_prjs = [project for project in data.keys()]

    # Normal Mode
    sp_normal = sp.add_parser('normal',
        aliases=[*existing_prjs],
        description='View or modify projects, sections, and tasks.',
        help='View or modify existing projects, sections, and tasks')
    mutual = sp_normal.add_mutually_exclusive_group()

    sp_normal.set_defaults(project=sys.argv[1], create=False, delete=False, archive=False)
    sp_normal.add_argument('-a', '--add')
    sp_normal.add_argument('-r', '--rename')


    mutual.add_argument('section', nargs='?')
    mutual.add_argument('-d', '--taskdelete', type=int, dest='task_delete')
    mutual.add_argument('-c', '--check')
    mutual.add_argument('-u', '--uncheck')
    mutual.add_argument('-mp', '--move_to_proj', nargs=2)
    mutual.add_argument('-ms', '--move_to_sect', nargs=3)
    mutual.add_argument('-sa', '--sectionadd', dest='section_add')
    mutual.add_argument('-sd', '--sectiondelete', dest='section_delete')
    # mutual.add_argument('-sc', '--sectioncheck', dest='section_check')

    # Create Mode
    sp_create = sp.add_parser('create',
        description='Creates a new project.',
        help='Create a new project',
        add_help=False)
    sp_create.set_defaults(create=True, delete=False, archive=False, project=None, section=None)
    sp_create.add_argument('project', action='store', help='Name of project')

    # Delete Mode
    sp_delete = sp.add_parser('delete',
        description='Deletes an existing project.',
        help='Delete a project',
        add_help=False)
    sp_delete.set_defaults(delete=True, create=False, archive=False, project=None, section=None)
    sp_delete.add_argument('project', action='store', help='Name of project')

    # Archive Mode
    sp_archive = sp.add_parser('archive',
        description='Archive completed tasks.',
        help='Archive tasks',
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
        self.args = args
        self.menu = menu
        self.todo_file = todo_file
        self.project = args.project
        self.section = args.section

        with open(self.todo_file) as f:
            self.data = json.load(f)
            self.iter_data = list(self.data.items())
            if not self.data and not args.create:
                sys.exit('no projects exist.')

        if len(sys.argv) == 1:
            self.show()
        elif not args.create and not args.delete:
            if self.project or self.section:
                self.nonexistent_check()
            self.proj_sections, self.proj_tasks = self.find_project()
            self.proj_tasks = self.data[self.project]['tasks']

    # Helper functions

    def nonexistent_check(self):
        """Check for nonexistent project and section names.

        nonexistent project names in normal mode have to be handled at the
        parser, otherwise our subparsers mess up.
        """
        # Check project name (delete mode)
        if self.project not in self.data.keys() and not self.args.create:
            sys.exit(f'project "{self.project}" does not exist.')
        # Check section name
        elif self.section:
            proj_sections = [sect['name'] for sect in self.data[self.project]['sections']]
            if self.section not in proj_sections:
                sys.exit(f'section "{self.section}" does not exist in project '
                         f'"{self.project}".')

    def project_name_check(self, project_name):
        """Check for invalid project names (create/rename helper).

        Args:
            project_name: (String) Either self.project or self.args.rename.
        
        Returns:
            None
        """
        blacklist = ['archive', 'create', 'delete', 'init']
        existing_projects = [project for project in self.data.keys()]

        if not project_name.isalnum():
            sys.exit('invalid project name.')
        elif project_name in blacklist:
            sys.exit('error: restricted project name.')
        elif project_name in existing_projects:
            sys.exit(f'project "{project_name}" already exists.')
        elif len(project_name) > 45:
            sys.exit('project name is too long.')

    # These archive helper functions do not modify self.data, self.proj_sections, or
    #   self.proj_tasks in any way. This is due to differences in check list
    #   assignments, what project needs to be passed to each helper, and the extra
    #   step of updating check list values when archiving a section archiving. So
    #   any modification of those 3 variables are done within either in archive()
    #   or archive_projects().

    def get_updated_check(self, project):
        """Return an updated checked list (archive helper).
        
        If a section is specified, the checked list will only contain tasks in
        that section. Otherwise, a list with all checked items will be returned.
        
        Args:
            project: (dict) Project's name, sections, tasks, and check list.
        
        Returns:
            checked: (set) The completed tasks to be archived.
        """
        if self.section:
            for sect in self.proj_sections:
                if self.section == sect['name']:
                    sect_tasks = sect['tasks']
            checked = set(project['check']) & set(sect_tasks)
            if not checked:
                sys.exit(f'No completed tasks in section "{self.section}" of project "{self.project}".')
        else:
            checked = {task_num for task_num in project.get('check')}
            if self.project and not checked:
                sys.exit(f'No completed tasks in project "{self.project}".')
        return checked

    def delete_tasks(self, project, checked):
        """Return updated task list after deleting checked tasks (archive helper).

        old_tasks is also returned so that get_updated_sections() can map the
        new tasks with their old index position.
        
        Args:
            project:    (dict)   Project's name, sections, tasks, and check list.
            checked:    (set)    Completed tasks to delete.
        
        Returns:
            old_tasks: (list) All pre-existing t4asks.
            new_tasks: (dict) All tasks post-archive (value) and their position (key).
            """
        old_tasks = project['tasks']
        new_tasks = {}

        for task_num, task in project.get('tasks').items():
            if int(task_num) not in checked:
                new_tasks[str(len(new_tasks) + 1)] = task
        return old_tasks, new_tasks

    def get_updated_sections(self, project, sections, old_tasks, new_tasks, checked):
        """Get an updated section task list (archive helper).
        
        new_tnames is returned so that we can update remaining check list values.
        
        Args:
            project: (dict) All tasks and their position as keys.
            sections: (list) The current project's sections, which is either
                self.proj_sections is a section is specified, or project['sections']
                otherwise.
            old_tasks: (dict) Comprehensive task list before deleting checked tasks.
            new_tasks: (dict) Comprehensive task list after deleting checked tasks.
            checked: (set) Updated check list.
        
        Returns:
            all_sect_tasks: (dict) Each section (name as key) and its unchecked
                tasks.
            new_tnames: (list) All task names after archiving."""
        new_tnames = list(new_tasks.values())
        all_sect_tasks = {}

        # Create new section list with unchecked tasks for the current project
        for sect in sections:
            unchecked_sect_tasks = list(set(sect['tasks']) - checked)
            for i, task_num in enumerate(unchecked_sect_tasks):
                old_tname = old_tasks.get(str(task_num))
                unchecked_sect_tasks[i] = new_tnames.index(old_tname) + 1
            all_sect_tasks[sect['name']] = sorted(unchecked_sect_tasks)
        return all_sect_tasks, new_tnames

    # General functions

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

        # If we're not archiving and there are completed tasks,
        # or if we are archiving, but a section is specified.
        if tasks and not self.args.archive or (self.args.archive and self.args.section):
            return (*sections, dict(*tasks))
        else:
            return (None, None)

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

    def create(self):
        """Create a new project."""
        self.project_name_check(self.project)
        self.data[self.project] = {"sections": [], "tasks": {}, "check": []}
        self.write()

    def delete(self):
        """Delete a project."""
        self.data.pop(self.project)
        self.write()

    def rename(self):
        """Rename a project or section."""
        self.project_name_check(self.args.rename)

        new_data = {}
        for name, prj in self.data.items():
            if self.section:
                new_data[name] = prj  # maybe put and AND somewhere up there
                if self.project == name:
                    for i, section in enumerate(prj['sections']):
                        if self.section == section['name']:
                            new_data[name]['sections'][i]['name'] = self.args.rename 
            else:
                if self.project == name:
                    new_data[self.args.rename] = prj
                else:
                    new_data[name] = prj
        self.data = new_data
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

              or we can fix get_updated_sections() so that it returns an updated
              copy of self.proj_sections.

              Or we can just not change self.proj_sections/tasks since we aren't
              going to call self.show().
        
        Args:
            None

        Returns:
            None
        """
        #   Exit if there's no completed tasks and we're archiving all projects.
        #   Also, avoid exiting if there are checked tasks in a non-1st project.
        if not self.project:
            all_checked_tasks = [task for prj in self.data.values() for task in prj['check']]
            if not all_checked_tasks:
                sys.exit('no completed tasks in any project.')

        if self.section:
            # Update check list
            project = self.data[self.project]
            checked = self.get_updated_check(project)
            project['check'] = list(set(project['check']) - checked)

            # Delete tasks
            old_tasks, new_tasks = self.delete_tasks(project, checked)
            project['tasks'] = new_tasks

            # Update sections
            all_sect_tasks, new_tnames = self.get_updated_sections(project, 
                self.proj_sections, old_tasks, new_tasks, checked)
            for sect in self.proj_sections:
                if sect['name'] in all_sect_tasks.keys():
                    sect['tasks'] = all_sect_tasks.get(sect['name'])

            # Update check list values
            for i, task in enumerate(project['check']):
                old_tnames = old_tasks.get(str(task))
                project['check'][i] = new_tnames.index(old_tnames) + 1
        elif self.project:
            self.archive_projects(self.data[self.project])
        else:
            for name, project in self.data.items():
                self.archive_projects(project)

        self.write()

    def archive_projects(self, project):
        """Delete completed tasks for projects.
        
        Args:
            project: (dict) A project's sections, tasks, and check list.
        
        Returns:
            None
        """
        # Empty check list
        checked = self.get_updated_check(project)
        project['check'] = []

        # Delete tasks
        old_tasks, new_tasks = self.delete_tasks(project, checked)
        project['tasks'] = new_tasks

        # Update sections
        all_sect_tasks, new_tnames = self.get_updated_sections(project,
            project['sections'], old_tasks, new_tasks, checked)
        for sect in project['sections']:
            if sect['name'] in all_sect_tasks.keys():
                sect['tasks'] = all_sect_tasks.get(sect['name'])


    # Task functions

    def add(self, label, project, section=None):
        """Add a task to a project.

        If a section is specified, the task's number will be added to the
          corresponding section's key `task` to indicate it's a section task.
        """
        proj_tasks = self.data[project]['tasks']
        if label in proj_tasks.values():
            sys.exit(f'task "{label}" already exists in project "{project}"')

        # add task
        proj_tasks[len(proj_tasks) + 1] = label
        self.write()

        # update section if a section task is added
        if section:
            for sect in self.data[project]['sections']:
                if section == sect.get('name'):
                    sect['tasks'].append(len(proj_tasks))
                    self.write()

    def task_delete(self):
        """Delete a task from a project."""
        position = self.args.task_delete
        if position > len(self.proj_tasks):
            sys.exit(f'project "{self.project}" has no task #{position}.')
        else:
            # delete task
            self.proj_tasks.pop(str(position))

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
            new_tasks = {}
            for old_index, task in self.proj_tasks.items():
                if position <= int(old_index):
                    new_index = str(int(old_index) - 1)
                    new_tasks[new_index] = task
                else:
                    new_tasks[old_index] = task
            self.data[self.project]['tasks'] = new_tasks

            self.write()

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
                        sys.exit(f'task "{label}" is already checked.')
        else:
            sys.exit(f'task "{label}" does not exist.')

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
                        sys.exit(f'task "{label}" is not checked.')
        else:
            sys.exit(f'task "{label}" does not exist.')

    def move_task(self):
        ttm = self.args.move_to_proj if self.args.move_to_proj else self.args.move_to_sect
        ttm_pos = len(self.proj_tasks)
        new_tasks = {}

        # project check
        if ttm[1] not in [project for project in self.data.keys()]:
            sys.exit(f'error: project "{ttm[1]}" does not exist')

        # section check
        existing_sects = [sect['name'] for sect in self.data[ttm[1]]['sections']]
        if self.args.move_to_sect and ttm[2] not in existing_sects:
            sys.exit(f'error: section "{ttm[2]}" does not exist in project "{ttm[1]}"')
        
        # find task
        for pos, task in self.proj_tasks.items():
            if task == ttm[0]:
                ttm_pos = pos
            else:
                new_pos = int(pos) if int(pos) < int(ttm_pos) else int(pos)-1
                new_tasks[new_pos] = task
        self.data[self.project]['tasks'] = new_tasks
        self.proj_tasks.pop(ttm_pos)

        # update check
        if int(ttm_pos) in self.data[self.project]['check']:
            self.data[self.project]['check'].remove(int(ttm_pos))
        for i,v in enumerate(self.data[self.project]['check']):
            self.data[self.project]['check'][i] = v if v < int(ttm_pos) else v-1

        # update sections
        for i,sect in enumerate(self.proj_sections):
            new_sects = []
            for task_num in sect['tasks']:
                if int(ttm_pos) > task_num:
                    new_sects.append(task_num)
                elif int(ttm_pos) < task_num:
                    new_sects.append(task_num-1)
            self.proj_sections[i]['tasks'] = new_sects

        # Add (writes to file there)
        if self.args.move_to_proj:
            self.add(ttm[0], ttm[1])
        else:
            self.add(ttm[0], ttm[1], ttm[2])

    # >>> Section functions

    def section_add(self):
        """Add a section."""
        label = self.args.section_add
        if label in [sect.get('name') for sect in self.proj_sections]:
            sys.exit(f'section "{label}" already exists in project "{self.project}".')

        sections = self.data[self.project]['sections']
        sections.append({"name": label, "tasks": []})
        self.write()

    def section_delete(self):
        """Delete a section."""
        label = self.args.section_delete

        if label not in [sect.get('name') for sect in self.proj_sections]:
            sys.exit(f'section "{label}" does not exist in project "{self.project}".')

        sections = self.data[self.project]['sections']
        check = self.data[self.project]['check']

        # delete section and section tasks
        for i, sect in enumerate(sections):
            if label == sect.get('name'):
                del sections[i]
                for task in sect.get('tasks'):
                    self.proj_tasks.pop(str(task))
                self.data[self.project]['check'] = list(set(check) - set(sect.get('tasks')))

        # update task indices
        new_tasks = {}
        for i,task_num in enumerate(self.proj_tasks.keys()):
            if len(self.proj_tasks.keys()) > i:
                new_tasks[str(i+1)] = self.proj_tasks.get(task_num)
        self.data[self.project]['tasks'] = new_tasks

        # update check list
        for i, task_num in enumerate(self.data[self.project]['check']):
            task = self.proj_tasks[str(task_num)]
            for tnum, t in self.data[self.project]['tasks'].items():
                if t == task:
                    self.data[self.project]['check'][i] = tnum

        # update sections
        all_sect_tasks, new_tnames = self.get_updated_sections(
                                       self.data[self.project],
                                       self.data[self.project]['sections'],
                                       self.proj_tasks,
                                       self.data[self.project]['tasks'],
                                       set(self.data[self.project]['check']))
        for sect in self.data[self.project]['sections']:
            sect['tasks'] = all_sect_tasks.get(sect['name'])
        
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
                       "b": (17, 18, 19, 20, 21, 22, 23, 24),
                       "v": (25, 26, 27, 28, 29, 30, 31, 32)}

        # Prefixes
        self.hash   = '     # '
        self.check  = '     ✓ '
        self.utask  = '     □ '
        self.blank  = '{}\n'.format(' ' * 56)

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

        # Violet
        curses.init_pair(25, 171, 141)
        curses.init_pair(26, 219, 141)
        curses.init_pair(27, 253, 141)
        curses.init_pair(28, -1, 97)
        curses.init_pair(29, 253, 97)
        curses.init_pair(30, 171, 97)
        curses.init_pair(31, 210, 97)
        curses.init_pair(32, 46, 97)

    def draw_banner(self, stdscr, clrs, proj_color, proj_name, end_banner):
        """Draw the TODO project's banner.

        The banner includes the "!!!"  prefix, the project's color label (e.g.,
          r, g, b), and and project's name.

        Args:
            stdscr: (Window) Represents the entire screen.
            clrs: (tuple) 8 sequential numbers that corresponds to the proper
                curses color pair.
            proj_color: (String) Color of project (e.g., r, g, b).
            proj_name: (String) Name of project.
            end_banner: (String) A line full of spaces to finish the banner.

        Returns:
            None
        """
        end_banner = '"{}\n'.format(' ' * (56 - len(proj_name) - 9))
        self.win.addstr(' !!! ', curses.color_pair(clrs[0]))
        self.win.addstr(f'{proj_color} ', curses.A_BOLD | curses.color_pair(clrs[1]))
        self.win.addstr('"', curses.color_pair(clrs[0]))
        self.win.addstr(proj_name, curses.A_BOLD | curses.color_pair(clrs[2]))
        self.win.addstr(end_banner, curses.color_pair(clrs[0]))

    def draw_tasks(self, stdscr, task_num, tname, check_list, clrs, section=False):
        """Draw regular and section tasks.

        Args:
            stdscr: (Window) Represents the entire screen.
            task_num: (int) The current task's index.
            tname: (String) Name of task.
            check_list: (list) Contains task indices that are marked as checked.
            clrs: (tuple) 8 sequential numbers that corresponds to the proper
                curses color pair.
            section: (boolean) Indicates whether the current task is a regular
                or section task.
        """
        # The suffix assignments here are strictly for tasks with less than
        # `length` chars.
        length = 42 if section else 44
        prefix = '  ' if section else ''
        tname_length = ' ' * (56 - len(tname) - (len(prefix) + 7))
        suffix = f'{tname_length}\n'

        if len(tname) > length:
            for line, substr in enumerate(textwrap.wrap(tname, width=length)):
                substr_length = ' ' * (56 - len(substr) - (len(prefix) + 7))
                suffix = f'{substr_length}\n'

                if line == 0:
                    if task_num in check_list:
                        self.win.addstr(f'{prefix}{self.check}', curses.color_pair(clrs[7]))
                        self.win.addstr(f'{substr}{suffix}', curses.color_pair(clrs[4]))
                    else:
                        self.win.addstr(f'{prefix}{self.utask}{substr}{suffix}', curses.color_pair(clrs[4]))
                else:
                    self.win.addstr(f'{prefix}       {substr}{suffix}', curses.color_pair(clrs[4]))
        else:
            if task_num in check_list:
                self.win.addstr(f'{prefix}{self.check}', curses.color_pair(clrs[7]))
                self.win.addstr(f'{tname}{suffix}', curses.color_pair(clrs[4]))
            else:
                self.win.addstr(f'{prefix}{self.utask}{tname}{suffix}', curses.color_pair(clrs[4]))

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
                proj_color = list(self.colors.keys())[i % len(self.colors)]
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
            self.win.addstr(self.blank * 2, curses.color_pair(clrs[3]))
        elif project:
            # sections and section tasks
            for sect in proj_sections:
                wrapper(self.draw_sections, check_list, clrs, proj_tasks, sect)
            if proj_sections:
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))

            # tasks
            for task_num, tname in proj_tasks.items():
                if task_num not in section_tasks:
                    wrapper(self.draw_tasks, int(task_num), tname, check_list, clrs, section=False)

            # end lines
            #   If there are regular tasks, we need to add 3 blank lines,
            #   otherwise just add 1 since draw_sections() adds 2 already (one
            #   between sections and one right before tasks).
            body_end = 3 if set(proj_tasks.keys()) - section_tasks else 1
            self.win.addstr(self.blank * body_end, curses.color_pair(clrs[3]))

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
        # The reason we have to use enumerate(projects) and thus iter_projects
        # during assignment is so we can get the correct proj_color with i.
        for i, proj in enumerate(projects):
            proj_sections = iter_projects[i][1]['sections']
            proj_tasks = iter_projects[i][1]['tasks']
            proj_name = iter_projects[i][0]
            section_tasks = {str(num) for sect in proj_sections for num in sect.get('tasks')}
            check_list = projects.get(proj).get('check')
            proj_color = list(self.colors.keys())[i % len(self.colors)]
            clrs = self.colors.get(proj_color)

            # Banner
            end_banner = '"{}\n'.format(' ' * (56 - len(proj_name) - 9))
            wrapper(self.draw_banner, clrs, proj_color, proj_name, end_banner)

            # Pre-body
            self.win.addstr(self.blank * 2, curses.color_pair(clrs[3]))

            # Body
            #   section
            for sect in proj_sections:
                wrapper(self.draw_sections, check_list, clrs, proj_tasks, sect)

            #   tasks
            if proj_sections:
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))
            for task_num, tname in proj_tasks.items():
                if task_num not in section_tasks:
                    wrapper(self.draw_tasks, int(task_num), tname, check_list, clrs, section=False)

            #   end lines
            body_end = 3 if set(proj_tasks.keys()) - section_tasks else 1
            self.win.addstr(self.blank * body_end, curses.color_pair(clrs[3]))

            # Project spacing
            self.win.addstr(' ' * self.width)
            self.win.addstr(' ' * self.width)

        # Block
        self.win.getch()

"""
[+++++++++++++++++++++++++++++++++++++++++++++]
                   Main
[+++++++++++++++++++++++++++++++++++++++++++++]
"""
def check_if_todo_repo(todo_file):
    """Check for a .todo configuration file.
    
    If the user runs `todo init`, create a .todo file if one doesn't exist,
      otherwise exit with an error.

    Any other `todo` command in a non-todo repository will exit with an error.

    Args:
        todo_file (String): The absolute path of the .todo configuration file.

    Returns:
        None
    """
    todo_dir = todo_file.split("/.todo")[0]
    if len(sys.argv) == 2 and sys.argv[1] == 'init':
            if not Path(todo_file).exists():
                Path(todo_file).write_text('{}')
                sys.exit(0)
            else:
                sys.exit(f'error: "{todo_dir}" is already a todo respository.')
    elif len(sys.argv) > 2 and sys.argv[1] == 'init':
        sys.exit('error: invalid initialization.')

def main(todo_file):
    """Main program, used when run as a script."""
    check_if_todo_repo(todo_file)

    menu = wrapper(Menu)
    parser = create_parser(menu, todo_file)

    todo = Todo(menu, parser, todo_file)

    if parser.create:
        todo.create()
    elif parser.delete:
        todo.delete()
    elif parser.archive:
        todo.archive()
    else:
        if parser.add:
            todo.add(parser.add, parser.project, parser.section)
        elif parser.task_delete:
            todo.task_delete()
        elif parser.check:
            todo.check()
        elif parser.uncheck:
            todo.uncheck()
        elif parser.move_to_proj or parser.move_to_sect:
            todo.move_task()
        elif parser.section_add:
            todo.section_add()
        elif parser.section_delete:
            todo.section_delete()
        elif parser.rename:
            todo.rename()
        elif parser.project or (parser.project and parser.section):
            try:
                todo.show()
            except:
                sys.exit('Error: Terminal window is not large enough.')


if __name__ == '__main__':
    full_path = os.path.realpath(__file__)
    main(todo_file=f'{os.path.dirname(full_path)}/.todo')

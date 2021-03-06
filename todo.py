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
import logging
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

        Args:
            message: (String) The default argparse error message raised.
        """
        error_msg_left = message.split(':')[0]
        error_msg_right = message.split(':')[1]

        if error_msg_left == 'invalid choice':
            sys.exit(f'project "{sys.argv[1]}" does not exist.')
        elif (error_msg_left == 'the following arguments are required' or
              error_msg_right == ' expected one argument'):
            sys.exit(message) 
        elif error_msg_left == 'unrecognized arguments':
            extra_args = error_msg_right.split(' ')[1:]
            suffix = '' if len(extra_args) == 1 else 's'
            if len(extra_args) == 1:
                extra_args = "'{}'".format(extra_args[0])
            else:
                extra_args = "'{}'".format("', '".join(extra_args))
            sys.exit(f'error: unrecognized argument{suffix} {extra_args}.')
        elif error_msg_left == 'argument section':
            sys.exit('error: too many arguments.')
        else:
            sys.exit(f'UNKNOWN ERROR: {message}.')

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
    -r LABEL                     Rename a project or section.

  tasks
    -a  LABEL                    Add a task.
    -d  ID [ID ...]              Delete tasks.
    -c  ID [ID ...]              Mark tasks as complete.
    -u  ID [ID ...]              Mark tasks as incomplete.
    -mp ID PROJECT               Move a task to a different project.
    -ms ID PROJECT SECTION       Move a task to a different section.

  sections
    -sa LABEL                    Add a section.
    -sd LABEL                    Delete a section.
    -us ID [ID ...]              Move tasks out of sections.
''')

def create_parser(menu, todo_file):
    """Create a command-line parser.

    For a custom usage menu and error handling, uses an overridden
      ArgumentParser instance.

    Args:
        menu: (Menu) Instance of our curses wrapped drawing class.
        todo_file: (String) Absolute path of the .todo configuration file.

    Returns:
        A Namespace object containing the command-line flags and their state.
    """
    parser = ArgumentParser()
    sp = parser.add_subparsers()

    # If in normal mode and no proj/sect is specified, display all projects
    if len(sys.argv) == 1: 
        parser.set_defaults(project=None, section=None, create=None)
        try:
            Todo(menu, parser.parse_args(), todo_file)
        except curses.error as e:
            sys.exit('error: terminal window is not large enough.')
        sys.exit(0)

    with open(todo_file) as f:
        existing_projects = [project for project in json.load(f).keys()]

    # Normal Mode
    sp_normal = sp.add_parser('normal',
        aliases=[*existing_projects],
        description='View or modify projects, sections, and tasks.',
        help='View or modify existing projects, sections, and tasks')
    sp_normal.set_defaults(project=sys.argv[1], create=False, delete=False, archive=False)
    sp_normal.add_argument('-a', '--add')
    sp_normal.add_argument('-r', '--rename')
    sp_normal.add_argument('-i', '--insert', nargs=2)

    section = sp_normal.add_mutually_exclusive_group()
    section.add_argument('section', nargs='?')
    section.add_argument('-d', '--taskdelete', type=int, nargs=argparse.REMAINDER, dest='task_delete')
    section.add_argument('-c', '--check', type=int, nargs=argparse.REMAINDER)
    section.add_argument('-u', '--uncheck', type=int, nargs=argparse.REMAINDER)
    section.add_argument('-mp', '--move_to_proj', nargs=2)
    section.add_argument('-ms', '--move_to_sect', nargs=3)
    section.add_argument('-sa', '--sectionadd', dest='section_add')
    section.add_argument('-sd', '--sectiondelete', dest='section_delete')
    section.add_argument('-us', '--unsect', type=int, nargs=argparse.REMAINDER)
    # section.add_argument('-sc', '--sectioncheck', dest='section_check')

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
        menu:      (Menu)       Instance of our curses wrapped drawing class.
        args:      (Namespace)  Contains command-line flags and their states.
        todo_file: (String)     Absolute path of the .todo configuration file.

    Attributes:

        menu:          (Menu)      see arg: menu
        args:          (Namespace) see arg: args
        todo_file:     (String)    see arg: todo_file
        project:       (String)    Name of project to view or modify.
        section:       (String)    Name of section to create, view, or modify.
        data:          (dict)      Contents of 'todo_file'.
        iter_data:     (list)      List representation of 'data'. (for indexing)
        proj_sections: (list)      Contains dicts with section names as keys and
                                     section tasks as values.
        proj_tasks:    (dict)      Task number as keys, task label as values.
    """
    def __init__(self, menu, args=None, todo_file=None):
        """Constructor. See class docstring."""
        self.menu = menu
        self.args = args
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
            # For getting a project's sections and tasks, which modes Create
            #   and Delete don't need.
            if self.project:
                self.nonexistent_check()
                self.proj_sections = self.data[self.project]['sections']
                self.proj_tasks = self.data[self.project]['tasks']
                self.check_list = self.data[self.project]['check']

    def __repr__(self):
        """Return attributes.

        If Todo is ran with Create or Delete mode, self.proj_sections and
          self.proj_tasks won't exist and will therefore throw an error.
          May want to fix that.
        """
        return (f'Todo({self.menu}, {self.args}, {self.todo_file}, '
                f'{self.project}, {self.section}, {self.data}, {self.iter_data}'
                f'{self.proj_sections}, {self.proj_tasks})')

    # Helper functions

    def nonexistent_check(self):
        """Check for nonexistent project and section names.

        Nonexistent project names in Normal mode have to be handled at the
          parser, otherwise our subparsers mess up. Note that this does NOT
          include moving tasks (which is in Normal mode).

        Nonexistent project names in Delete mode are handled in todo.delete().

        Helper:
            todo.__init__()
        """
        if self.project not in self.data.keys():
            # Check project name (archive mode)
            sys.exit(f'error: project "{self.project}" does not exist.')
        elif self.section:
            # Check section name (normal, archive mode)
            if self.section not in self.data[self.project]['sections'].keys():
                sys.exit(f'error: section "{self.section}" does not exist in project "{self.project}".')

    def project_name_check(self, project_name):
        """Check for invalid project names.

        Helper:
            todo.create()
            todo.rename()

        Args:
            project_name: (String) Either self.project or self.args.rename.
        """
        blacklist = ['archive', 'create', 'delete']
        existing_projects = [project for project in self.data.keys()]

        if not project_name.isalnum():
            sys.exit('error: invalid project name.')
        elif project_name in blacklist:
            sys.exit('error: restricted project name.')
        elif project_name in existing_projects:
            sys.exit(f'error: project "{project_name}" already exists.')
        elif len(project_name) > 45:
            sys.exit('error: project name is too long.')

    # These archive helper functions do not modify self.data, self.proj_sections, or
    #   self.proj_tasks in any way. This is due to differences in check list
    #   assignments, what project needs to be passed to each helper, and the extra
    #   step of updating check list values when archiving a section archiving. So
    #   any modification of those 3 variables are done within either in archive()
    #   or archive_projects().

    def get_updated_check(self, project):
        """Return an updated checked list (archive helper).
        
        If a section is specified, the checked list returned will only contain
          tasks in that section. Otherwise, a list with all checked items will
          be returned.
        
        Args:
            project: (dict) Project's name, sections, tasks, and check list.
        
        Returns:
            checked: (set) The completed tasks to be archived.
        """
        if self.section:
            sect_tasks = self.proj_sections[self.section]
            checked = set(project['check']) & set(sect_tasks)
            if not checked:
                sys.exit(f'No completed tasks in section "{self.section}" of project "{self.project}".')
        else:
            checked = {task_num for task_num in project.get('check')}
            if not checked:
                sys.exit(f'No completed tasks in project "{self.project}".')
        return checked

    @staticmethod
    def no_checked_tasks(project, checked):
        """Get an updated task list with no checked tasks.
        
        Helper:
            archive()

        Args:
            project: (dict) Project's name, sections, tasks, and check list.
            checked: (set)  Completed tasks to delete.
        
        Returns:
            old_tasks: (list) All pre-existing tasks. (to map new tasks with
                                old task positions)
            new_tasks: (dict) All tasks post-archive (as value) and their
                                position (as key).
            """
        old_tasks = project['tasks']
        new_tasks = {}

        for task_num, task in project.get('tasks').items():
            if int(task_num) not in checked:
                new_tasks[str(len(new_tasks) + 1)] = task
        return old_tasks, new_tasks

    @staticmethod
    def get_updated_sections(sections, old_tasks, new_tasks, checked):
        """Get an updated section task list after completed tasks are removed.
                
        Helper:
            section_delete()
            archive()
            archive_projects()

        Args:
            sections:  (list) The current project's sections, which is either
                                self.proj_sections if a section is specified,
                                or project['sections'] otherwise.
            old_tasks: (dict) Task list before task indices are updated.
            new_tasks: (dict) Task list after task indices are updated.
            checked:   (set)  Updated check list.
        
        Returns:
            all_sections: (dict) Each section (name as key) and its unchecked
                                   tasks (as values) after archiving.
            new_tnames:   (list) All task names after archiving. (for updating
                                   remaining check list values in Archive???)
        """
        new_tnames = list(new_tasks.values())
        all_sections = {}

        for sect_name, sect_tasks in sections.items():
            unchecked_sect_tasks = list(set(sect_tasks) - checked)
            for i, task_num in enumerate(unchecked_sect_tasks):
                old_tname = old_tasks[str(task_num)]
                unchecked_sect_tasks[i] = new_tnames.index(old_tname) + 1
            all_sections[sect_name] = sorted(unchecked_sect_tasks)

        return all_sections, new_tnames

    # General functions

    def write(self):
        """Write changes to todo's configuration file..

        Normally, it will be .todo. However, when testing, it'll use the test
          file .test_todo.
        """
        with open(self.todo_file, 'w') as f:
            json.dump(self.data, f)

    def show(self):
        """Display TODO list.

        There are 3 scenarios based on the arguments passed:

            a)   $ todo project section
            b)   $ todo project
            c)   $ todo

        a) displays the section specified and its tasks.
        b) displays the project specified, all sections within it, and all
             tasks.
        c) displays all projects, their sections, and all of their tasks.

        Tasks belonging to a section will be excluded from the general task
          output area since they're already included in the section task area.
        """
        if self.project or self.section:
            wrapper(self.menu.draw_prjsect,
                    self.data,
                    self.proj_sections,
                    self.proj_tasks,
                    self.project,
                    self.section)
        else:
            wrapper(self.menu.draw_all, self.data)
    
    def create(self):
        """Create a new project."""
        self.project_name_check(self.project)
        self.data[self.project] = {"sections": {}, "tasks": {}, "check": []}
        self.write()

    def delete(self):
        """Delete a project."""
        try:
            del self.data[self.project]
        except KeyError as e:
            sys.exit(f'error: project "{self.project}" does not exist.')
        self.write()

    def archive(self):
        """Delete completed tasks.

        project[x] assignments modify self.data, which is what is eventually
          written to 'todo_file'.
        """
        # Exit if we're archiving all projects and there are no completed tasks
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
            old_tasks, new_tasks = self.no_checked_tasks(project, checked)
            project['tasks'] = new_tasks

            # Update sections
            all_sections, new_tnames = self.get_updated_sections(self.proj_sections, old_tasks, new_tasks, checked)
            project['sections'] = all_sections

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

        project[x] assignments modify self.data, which is what is eventually
          written to 'todo_file'.

        Args:
            project: (dict) A project's sections, tasks, and check list.
        """
        # Empty check list
        checked = self.get_updated_check(project)
        project['check'] = []

        # Delete tasks
        old_tasks, new_tasks = self.no_checked_tasks(project, checked)
        project['tasks'] = new_tasks

        # Update sections
        all_sections, new_tnames = self.get_updated_sections(project['sections'], old_tasks, new_tasks, checked)
        project['sections'] = all_sections

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

    # Task functions

    def add(self, label, project, section=None):
        """Add a task to a project.

        Args:
            label:   (String) Name of task to be added.
            project: (String) Name of project to add task to.
            section: (String) Name of section to add task to.
        """
        proj_tasks = self.data[project]['tasks']

        # existing task check
        if label in self.data[project]['tasks'].values():
            sys.exit(f'task "{label}" already exists in project "{project}".')

        # update section
        # self.proj_section isn't used here since move_task also uses this and
        # we may need to add to section in a different project
        if section:
            self.data[project]['sections'][section].append(len(proj_tasks) + 1)

        # add task
        proj_tasks[len(proj_tasks) + 1] = label

        self.write()

    def insert(self):
        """Insert a task at a specified position."""
        pos, label = self.args.insert

        # insert format check
        if not pos.isdigit():
            sys.exit(f'error: insert position must be a digit')

        # existing task check
        if label in self.proj_tasks.values():
            sys.exit(f'error: task "{label}" already exists in project "{self.project}".')

        # valid position check
        if int(pos) > int(list(self.proj_tasks.keys())[-1]):
            sys.exit(f'error: there are only {list(self.proj_tasks.keys())[-1]} task positions.')

        # update section positions
        all_section_tasks = [tasks for tasks in self.proj_sections.values()]

        for sect_tasks in all_section_tasks:
            for i, task_num in enumerate(sect_tasks):
                if task_num >= int(pos):
                    sect_tasks[i] = task_num + 1

        # update check list
        for i, task_num in enumerate(self.check_list):
            if task_num >= int(pos):
                self.check_list[i] = task_num + 1

        # update task list positions and add task
        new_tasks = {}
        for old_index, task in self.proj_tasks.items():
            if int(old_index) == int(pos):
                new_tasks[pos] = label
                new_index = str(int(old_index) + 1)
                new_tasks[new_index] = task
            elif int(old_index) > int(pos):
                new_index = str(int(old_index) + 1)
                new_tasks[new_index] = task
            else:
                new_tasks[old_index] = task
        self.data[self.project]['tasks'] = new_tasks

        if self.section:
            for i, sect_num in enumerate(self.proj_sections[self.section]):
                if sect_num > int(pos):
                    self.proj_sections[self.section].insert(i, int(pos))
                    break

        self.write()

    def task_delete(self):
        """Delete a task from a project."""
        labels = list(sorted(self.args.task_delete))
        
        # checks
        for label in labels:
            if not label:
                sys.exit('error: 0 is an invalid task number.')
            elif label > len(self.proj_tasks):
                sys.exit(f'project "{self.project}" has no task #{label}.')
        
        # reduce non-first task indices by 1 to ensure proper
        # deletion after deletion of the previous task
        for i, label in enumerate(labels):
            if i != 0:
                labels[i] = label - len(labels[:i])

        for label in labels:
            # delete task
            self.proj_tasks.pop(str(label))

            # update sections
            all_section_tasks = [tasks for tasks in self.proj_sections.values()]

            for sect_tasks in all_section_tasks:
                if label in sect_tasks:
                    sect_tasks.remove(label)
                for i, task_num in enumerate(sect_tasks):
                    if task_num > label:
                        sect_tasks[i] = task_num - 1

            # update check list
            if label in self.check_list:
                self.check_list.remove(label)

            for i, task_num in enumerate(self.check_list):
                if task_num > label:
                    self.check_list[i] = task_num - 1

            # update task list label numbers
            new_tasks = {}
            for old_index, task in self.proj_tasks.items():
                if label <= int(old_index):
                    new_index = str(int(old_index) - 1)
                    new_tasks[new_index] = task
                else:
                    new_tasks[old_index] = task
            self.data[self.project]['tasks'] = new_tasks
            self.proj_tasks = new_tasks

        self.write()

    def check_uncheck(self, check):
        """Mark a task as checked or unchecked.

        Args:
            check: (boolean) Indicates whether to check (True) or uncheck
                               (False) a task.

        """
        labels = self.args.check if check else self.args.uncheck
        task_id_list = list(self.proj_tasks.keys())

        for label in labels:
            if str(label) in task_id_list:
                if check:
                    if label not in self.check_list:
                        self.check_list.append(label)
                    else:
                        sys.exit(f'task #{label} is already checked.')
                else:
                    if label in check_list:
                        self.check_list.remove(label)
                    else:
                        sys.exit(f'task #{label} is not checked.')
            else:
                sys.exit(f'task #{label} does not exist.')

        self.write()

    def move_task(self):
        """Move a task to a different project or section.

        'ttm' is short for "task to move."

        If no section is specified (-mp), 'ttm' is a list of the format:
            [id, project]

        If a section is specified (-ms), 'ttm' is a list of the format:
            [id, project, section]
        """
        ttm = self.args.move_to_proj if self.args.move_to_proj else self.args.move_to_sect
        task_id = ttm[0]
        new_prj = ttm[1]
        new_sect = ttm[2] if self.args.move_to_sect else None
        new_tasks = {}

        # Nonexistent checks
        if task_id not in self.proj_tasks.keys():
            sys.exit(f'error: task #{task_id} does not exist in project "{self.project}".')

        if new_prj not in [project for project in self.data.keys()]:
            sys.exit(f'error: project "{new_prj}" does not exist.')

        if self.args.move_to_sect:
            if new_sect not in self.data[new_prj]['sections'].keys():
                sys.exit(f'error: section "{new_sect}" does not exist in project "{new_prj}".')

        # Task exists checks
        moved_proj_tasks = self.data[new_prj]['tasks'].values()
        if self.args.move_to_sect:
            moved_sect_tasks = self.data[new_prj]['sections'][new_sect]

        #   if moving to a project
        if self.args.move_to_proj and self.proj_tasks[task_id] in moved_proj_tasks:
            sys.exit(f'error: task #{task_id} already exists in project "{new_prj}".')

        #   if moving to a section in the same project OR
        #   if moving to a different section in a different project
        if self.args.move_to_sect:
            if (
                (new_prj == self.project and int(task_id) in moved_sect_tasks)
                or
                (new_prj != self.project and self.proj_tasks[task_id] in moved_proj_tasks)
               ):
                sys.exit(f'error: task #{task_id} already exists in section "{new_sect}" of project "{new_prj}".')

        # Remove task
        for pos, task in self.proj_tasks.items():
            if task != self.proj_tasks[task_id]:
                new_pos = int(pos) if int(pos) < int(task_id) else int(pos) - 1
                new_tasks[new_pos] = task
        self.data[self.project]['tasks'] = new_tasks

        # Update check
        if int(task_id) in self.check_list:
            self.check_list.remove(int(task_id))
        for i, task_num in enumerate(self.data[self.project]['check']):
            self.check_list[i] = task_num if task_num < int(task_id) else task_num - 1

        # Update sections
        for sect_name, sect_tasks in self.proj_sections.items():
            new_sects = []
            for task_num in sect_tasks:
                if int(task_id) > task_num:
                    new_sects.append(task_num)
                elif int(task_id) < task_num:
                    new_sects.append(task_num - 1)
            self.proj_sections[sect_name] = new_sects

        # Add (writes to file there)
        if self.args.move_to_proj:
            self.add(self.proj_tasks.get(task_id), new_prj)
        else:
            self.add(self.proj_tasks.get(task_id), new_prj, new_sect)

    # >>> Section functions

    def section_add(self):
        """Add a section."""
        label = self.args.section_add
        if label in self.proj_sections.keys():
            sys.exit(f'section "{label}" already exists in project "{self.project}".')

        self.proj_sections[label] = []
        self.write()

    def section_delete(self):
        """Delete a section."""
        label = self.args.section_delete
        check = self.data[self.project]['check']

        if label not in self.proj_sections.keys():
            sys.exit(f'section "{label}" does not exist in project "{self.project}".')

        # delete section and section tasks
        sect_tasks = self.proj_sections.get(label)
        del self.proj_sections[label]
        for task in sect_tasks:
            self.proj_tasks.pop(str(task))
        self.data[self.project]['check'] = list(set(check) - set(sect_tasks))

        # update task indices
        new_tasks = {}
        for i, task_num in enumerate(self.proj_tasks.keys()):
            new_tasks[str(i+1)] = self.proj_tasks.get(task_num)
        self.data[self.project]['tasks'] = new_tasks

        # update check list
        for i, old_task_num in enumerate(self.data[self.project]['check']):
            for new_task_num, task in self.data[self.project]['tasks'].items():
                if task == self.proj_tasks[str(old_task_num)]:
                    self.data[self.project]['check'][i] = int(new_task_num)

        # update sections
        all_sections, new_tnames = self.get_updated_sections(
                                       self.proj_sections,
                                       self.proj_tasks,
                                       self.data[self.project]['tasks'],
                                       set(self.data[self.project]['check']))
        for sect_name, sect_tasks in self.proj_sections.items():
            self.proj_sections[sect_name] = all_sections.get(sect_name)

        self.write()

    def unsection(self):
        "Move tasks out of sections."
        for task_to_unsect in self.args.unsect:
            for sect_name, sect_tasks in self.proj_sections.items():
                if task_to_unsect in sect_tasks:
                    self.proj_sections[sect_name].remove(task_to_unsect)
        
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
        begin_x: (int) Starting x coordinate of the curses window.
        begin_y: (int) Starting y coordinate of the curses window.
        height: (int)  Height of curses window.
        width: (int)   Width of curses window.
        win: (Window)  A Window object to draw on.    
        colors: (dict) All current project colors (as keys) and their respective
                         color pairs initialized in init_colors().
        hash: (String)  Prefix for unchecked tasks.
        check: (String) Prefix for checked tasks.
        blank: (String) A blank line with the same length as the project box.
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
        self.colors = {"r": (1, 2, 3, 4, 5, 6, 7, 8, 9),
                       "g": (10, 11, 12, 13, 14, 15, 16, 17, 18),
                       "b": (19, 20, 21, 22, 23, 24, 25, 26, 27),
                       "v": (28, 29, 30, 31, 32, 33, 34, 35, 36)}

        # Prefixes
        self.hash   = '  # '
        self.check  = '  ✓ '
        self.utask  = '  □ '
        self.blank  = '{}\n'.format(' ' * 58)

    def __repr__(self):
        """Return attributes.

        We don't really need to return the prefixes do we?
        """
        return (f'Menu({self.begin_x}, {self.begin_y}, {self.height}, '
                f'{self.width}, {self.win}, {self.colors})')

    def init_colors(self):
        """Initialize custom curses color pairs.

        Color pair mapping:

            Let x = {1, 10, 19, 28},

                x:        ! and double quotes ("")
                x + 1:    Color letter (e.g., r, g, b)
                x + 2:    Project name
                x + 3:    Body background
                x + 4:    Task
                x + 5:    Hash
                x + 6:    Section name
                x + 7:    Checkmark
                x + 8:    Index
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
        curses.init_pair(9, 180, 131)

        # Green
        curses.init_pair(10, 76, 71)
        curses.init_pair(11, 119, 71)
        curses.init_pair(12, 253, 71)
        curses.init_pair(13, -1, 65)
        curses.init_pair(14, 253, 65)
        curses.init_pair(15, 76, 65)
        curses.init_pair(16, 210, 65)
        curses.init_pair(17, 46, 65)
        curses.init_pair(18, 180, 65)

        # Blue
        curses.init_pair(19, 75, 69)
        curses.init_pair(20, 45, 69)
        curses.init_pair(21, 253, 69)
        curses.init_pair(22, -1, 67)
        curses.init_pair(23, 253, 67)
        curses.init_pair(24, 75, 67)
        curses.init_pair(25, 210, 67)
        curses.init_pair(26, 46, 67)
        curses.init_pair(27, 180, 67)

        # Violet
        curses.init_pair(28, 171, 141)
        curses.init_pair(29, 219, 141)
        curses.init_pair(30, 253, 141)
        curses.init_pair(31, -1, 97)
        curses.init_pair(32, 253, 97)
        curses.init_pair(33, 171, 97)
        curses.init_pair(34, 210, 97)
        curses.init_pair(35, 46, 97)
        curses.init_pair(36, 180, 97)

    def draw_banner(self, stdscr, clrs, proj_color, proj_name, end_banner):
        """Draw the TODO project's banner.

        The banner includes the "!!!"  prefix, the project's color label (e.g.,
          r, g, b), and and project's name.

        Args:
            stdscr:     (Window)  Represents the entire screen.
            clrs:       (tuple)   8 sequential numbers that corresponds to the
                                    proper curses color pair.
            proj_color: (String)  Color of project (e.g., r, g, b).
            proj_name:  (String)  Name of project.
            end_banner: (String)  A line full of spaces to finish the banner.
        """
        end_banner = '"{}\n'.format(' ' * (56 - len(proj_name) - 9))
        self.win.addstr(' !!! ', curses.color_pair(clrs[0]))
        self.win.addstr(f'{proj_color}   ', curses.A_BOLD | curses.color_pair(clrs[1]))
        self.win.addstr('"', curses.color_pair(clrs[0]))
        self.win.addstr(proj_name, curses.A_BOLD | curses.color_pair(clrs[2]))
        self.win.addstr(end_banner, curses.color_pair(clrs[0]))

    def draw_tasks(self, stdscr, task_num, tname, check_list, clrs, section=False):
        """Draw regular and section tasks.

        Args:
            stdscr:     (Window)  Represents the entire screen.
            task_num:   (int).    The task's index.
            tname:      (String)  Name of task.
            check_list: (list)    Contains task numbers that are checked.
            clrs:       (tuple)   8 sequential numbers that correspond to the
                                    proper curses color pair.
            section:    (boolean) Indicates whether the current task is a
                                    regular or section task.
        """
        tindex = f'  {task_num}'
        # tindex = '    '
        length = 42 if section else 44  # amount of characters a task line can be
        # 'prefix' is the spacing after index but before □ or ✓. For substrings
        #   longer than 'length', we have to manually add spaces ('sub_space')
        #   since we're not drawing the index, which gives 3 or 4 spaces.
        prefix = ' ' * (9 - len(tindex)) if section else ' ' * (7 - len(tindex))
        if task_num < 10:
            suffix = f'{" " * (56 - len(tname) - (len(prefix) + 5))}\n'
        else:
            suffix = f'{" " * (56 - len(tname) - (len(prefix) + 6))}\n'

        if len(tname) > length:
            for line, substr in enumerate(textwrap.wrap(tname, width=length)):
                if task_num < 10:
                    suffix = f'{" " * (56 - len(substr) - (len(prefix) + 5))}\n'
                else:
                    suffix = f'{" " * (56 - len(substr) - (len(prefix) + 6))}\n'

                if line == 0:
                    if task_num in check_list:
                        self.win.addstr(f'{tindex}', curses.color_pair(clrs[8]))
                        self.win.addstr(f'{prefix}{self.check}', curses.color_pair(clrs[7]))
                        self.win.addstr(f'{substr}{suffix}', curses.color_pair(clrs[4]))
                    else:
                        self.win.addstr(f'{tindex}', curses.color_pair(clrs[8]))
                        self.win.addstr(f'{prefix}{self.utask}{substr}{suffix}', curses.color_pair(clrs[4]))
                else:
                    sub_space = ' ' * 7 if task_num < 10 else ' ' * 8
                    self.win.addstr(f'{prefix}{sub_space}{substr}{suffix}', curses.color_pair(clrs[4]))
        else:
            if task_num in check_list:
                self.win.addstr(f'{tindex}', curses.color_pair(clrs[8]))
                self.win.addstr(f'{prefix}{self.check}', curses.color_pair(clrs[7]))
                self.win.addstr(f'{tname}{suffix}', curses.color_pair(clrs[4]))
            else:
                self.win.addstr(f'{tindex}', curses.color_pair(clrs[8]))
                self.win.addstr(f'{prefix}{self.utask}{tname}{suffix}', curses.color_pair(clrs[4]))

    def draw_sections(self, stdscr, check_list, clrs, proj_tasks, sect_name,
                      sect_tasks):
        """Draw sections.

        Args:
            stdscr:     (Window) Represents the entire screen.
            check_list: (list)   Task indices for tasks marked as checked.
            clrs:       (tuple)  8 sequential numbers that correspond to the
                                   proper curses color pair.
            proj_tasks: (dict)   All tasks and their index for the specified
                                   project.
            sect:       (dict)   Name and tasks for the current section.
        """
        end_sec = '{}\n'.format(' ' * (56 - len(sect_name) - 9))

        # Section header
        self.win.addstr(f'{" " * 6} {self.hash}', curses.color_pair(clrs[5]))
        self.win.addstr(f'{sect_name}{end_sec}', curses.color_pair(clrs[6]))

        # Section tasks
        for task_num in sect_tasks:
            tname = proj_tasks.get(str(task_num))
            wrapper(self.draw_tasks, task_num, tname, check_list, clrs,
                    section=True)
        self.win.addstr(self.blank, curses.color_pair(clrs[3]))

    def draw_prjsect(self, stdscr, projects, proj_sections, proj_tasks, project, section):
        """Draw a specific project.

        If a section is specified, draw only the project, the specified section,
            and its tasks.

        Args:
            stdscr:        (Window) Represents the entire screen.
            proj_sections: (dict)   All section names and their tasks.
            proj_tasks:    (dict)   All tasks and their index for the specified
                                      project.
            project:       (String) Name of the specified project.
            section:       (String) Name of the specified section.
        """
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
            wrapper(self.draw_sections, check_list, clrs, proj_tasks, section,
                    proj_sections[section])

            # end lines
            self.win.addstr(self.blank * 2, curses.color_pair(clrs[3]))
        elif project:
            # sections and section tasks
            for sect_name, sect_tasks in proj_sections.items():
                wrapper(self.draw_sections, check_list, clrs, proj_tasks,
                        sect_name, sect_tasks)
            if proj_sections:
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))

            # tasks
            #   we str(task) cause proj_tasks' keys are Strings, and it'd be
            #   very annoying if we had to convert all_sect_tasks elements later
            all_sect_tasks = [str(task) for tasks in proj_sections.values() for task in tasks]

            for task_num, tname in proj_tasks.items():
                if task_num not in all_sect_tasks:
                    wrapper(self.draw_tasks, int(task_num), tname, check_list,
                            clrs, section=False)

            # end lines
            #   If there are regular tasks, we need to add 3 blank lines,
            #   otherwise just add 1 since draw_sections() adds 2 already (one
            #   between sections and one right before tasks).
            body_end = 3 if set(proj_tasks.keys()) - set(all_sect_tasks) else 1
            self.win.addstr(self.blank * body_end, curses.color_pair(clrs[3]))

        # Block
        self.win.getch()

    def draw_all(self, stdscr, projects):
        """Draw all projects, sections, and tasks.

        Args:
            stdscr:        (Window) Represents the entire screen.
            projects:      (dict)   All projects (as keys) and their sections and
                                      tasks (as values).
        """
        for i, proj_name in enumerate(projects):
            proj_sections = projects[proj_name]['sections']
            proj_tasks = projects[proj_name]['tasks']
            check_list = projects[proj_name]['check']
            proj_color = list(self.colors.keys())[i % len(self.colors)]
            clrs = self.colors.get(proj_color)

            # Banner
            end_banner = '"{}\n'.format(' ' * (56 - len(proj_name) - 9))
            wrapper(self.draw_banner, clrs, proj_color, proj_name, end_banner)

            # Pre-body
            self.win.addstr(self.blank * 2, curses.color_pair(clrs[3]))

            # Body
            #   section
            for sect_name, sect_tasks in proj_sections.items():
                wrapper(self.draw_sections, check_list, clrs, proj_tasks,
                        sect_name, sect_tasks)

            #   tasks
            all_sect_tasks = [str(task) for tasks in proj_sections.values() for task in tasks]
            if proj_sections:
                self.win.addstr(self.blank, curses.color_pair(clrs[3]))
            for task_num, tname in proj_tasks.items():
                if task_num not in all_sect_tasks:
                    wrapper(self.draw_tasks, int(task_num), tname, check_list,
                    clrs, section=False)

            #   end lines
            body_end = 3 if set(proj_tasks.keys()) - set(all_sect_tasks) else 1
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


def main(todo_file):
    """Main program, used when ran as a script."""
    logging.basicConfig(level=logging.DEBUG)
    menu = wrapper(Menu)
    parser = create_parser(menu, todo_file)
    todo = Todo(menu, parser, todo_file)

    # Non-normal modes
    if parser.create:
        todo.create()
    elif parser.delete:
        todo.delete()
    elif parser.archive:
        todo.archive()
    # Normal mode
    else:
        if parser.add:
            todo.add(parser.add, parser.project, parser.section)
        elif parser.task_delete or parser.task_delete == 0:
            todo.task_delete()
        elif parser.check or parser.uncheck:
            check = True if parser.check else False
            todo.check_uncheck(check)
        elif parser.move_to_proj or parser.move_to_sect:
            todo.move_task()
        elif parser.section_add:
            todo.section_add()
        elif parser.section_delete:
            todo.section_delete()
        elif parser.rename:
            todo.rename()
        elif parser.unsect:
            todo.unsection()
        elif parser.insert:
            todo.insert()
        elif parser.project or (parser.project and parser.section):
            # try:
            todo.show()
            # except:
            #     sys.exit('error: terminal window is not large enough.')


if __name__ == '__main__':
    todo_dir = os.path.dirname(os.path.realpath(__file__))
    todo_file = os.path.join(todo_dir, '.todo')
    try:
        main(todo_file=todo_file)
    except KeyboardInterrupt as e:
        sys.exit('keyboard interrupt: exiting')

import pytest
import sys
import todo
from todo import Todo

DEFAULT_CONTENTS = '{"test": {"sections": [{"name": "sect1", "tasks": [1]}], "tasks": {"1": "task1"}, "check": []}}'
TODO_FILE = 'test_catalog.json'


def test_main():
    # ERROR: Non-existent section
    with pytest.raises(SystemExit) as excinfo:
        todo.main(['test', 'nonexistentsection'], TODO_FILE)
    assert excinfo.type == SystemExit
    assert str(excinfo.value) == 'section "nonexistentsection" of project "test" does not exist.'

class TestParser(object):
    def test_create_parser_Create(self):
        # ERROR: No project given
        with pytest.raises(SystemExit) as excinfo:
            todo.create_parser(menu, ['--create'], TODO_FILE)
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'No project name given.'

        # ERROR: Invalid project name
        with pytest.raises(SystemExit) as excinfo:
            todo.create_parser(menu, ['--create', "_"], TODO_FILE)
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'Invalid project name.'

        # ERROR: Project already exists
        with pytest.raises(SystemExit) as excinfo:
            todo.create_parser(menu, ['--create', "test"], TODO_FILE)
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'Project "test" already exists.'

        # Successful
        parser, create = todo.create_parser(menu, ['--create', 'n3w'], TODO_FILE)
        assert create

    def test_create_parser_ProjectChecks(self):
        # ERROR: Nonexistent project
        with pytest.raises(SystemExit) as excinfo:
            todo.create_parser(menu, ['notaproject'], TODO_FILE)
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'Project "notaproject" does not exist.'

        # Successful
        parser, create = todo.create_parser(menu, ['test'], TODO_FILE)
        assert str(parser) == "Namespace(add=None, check=None, delete=None, project='test', section=None, section_add=None, section_check=None, section_delete=None, uncheck=None)"

    # def test_create_parser_InvalidOptionCombos(self):

class TestTodo(object):
    def update_file(self):
        with open(TODO_FILE, 'r') as f:
            data = f.readlines()
        with open(TODO_FILE, 'w') as f:  # reset file
            f.write(DEFAULT_CONTENTS)
        return data

    def test_find_project(self):
        parser, create = todo.create_parser(menu, menu, ['test'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        # Sections
        assert test_todo.find_project()[0] == [{'name': 'sect1', 'tasks': [1]}]
        # Tasks
        assert test_todo.find_project()[1] == {'1': 'task1'}

    def test_show_Section(self, capsys):
        parser, create = todo.create_parser(menu, ['test', 'nonexistentsection'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)

        # ERROR: Non-existent section
        with pytest.raises(SystemExit) as excinfo:
            test_todo.show()
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'section "nonexistentsection" does not exist in project "test".'

        # Successful
        parser, create = todo.create_parser(menu, ['test', 'sect1'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.show()
        captured = capsys.readouterr()
        assert captured.out == "test\n\t sect1\n\t\t task1\n"

    def test_show_Projects(self, capsys):
        # Project
        parser, create = todo.create_parser(menu, ['test'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.show()
        captured = capsys.readouterr()
        assert captured.out == "test\n\t sect1\n\t\t task1\n\n\t tasks\n"

        # All
        test_todo = Todo(todo_file=TODO_FILE)
        captured = capsys.readouterr()
        assert captured.out == "test\n\t sect1\n\t\t task1\n\n\t tasks\n---------------------------------------\n"

    def test_create(self):
        # Successful
        parser, create = todo.create_parser(menu, ['--create', 'test2'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.create()
        updated_file = self.update_file()
        assert updated_file == ['{"test": {"sections": [{"name": "sect1", "tasks": [1]}], "tasks": {"1": "task1"}, "check": []}, "test2": {"sections": [], "tasks": {}, "check": []}}']

    def test_add(self):
        # Normal task add
        parser, create = todo.create_parser(menu, ['test', '-a', 'task2'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.add('task2')
        updated_file = self.update_file()
        assert updated_file == ['{"test": {"sections": [{"name": "sect1", "tasks": [1]}], "tasks": {"1": "task1", "2": "task2"}, "check": []}}']

        # Section task add
        parser, create = todo.create_parser(menu, ['test', 'sect1', '-a', 'task2'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.add('task2')
        updated_file = self.update_file()
        assert updated_file == ['{"test": {"sections": [{"name": "sect1", "tasks": [1, 2]}], "tasks": {"1": "task1", "2": "task2"}, "check": []}}']

    def test_section_add(self):
        parser, create = todo.create_parser(menu, ['test', '-sa', "sect2"], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.section_add("sect2")
        updated_file = self.update_file()
        assert updated_file ==  ['{"test": {"sections": [{"name": "sect1", "tasks": [1]}, {"name": "sect2", "tasks": []}], "tasks": {"1": "task1"}, "check": []}}']

    def test_delete(self):
        # Setup
        parser, create = todo.create_parser(menu, ['test', '-sa', "sect2"], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.section_add("sect2")
        parser, create = todo.create_parser(menu, ['test', 'sect1', '-a', "task2"], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.add("task2")
        parser, create = todo.create_parser(menu, ['test', 'sect2', '-a', "task3"], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.add("task3")
        parser, create = todo.create_parser(menu, ['test', 'sect1', '-a', "task4"], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.add("task4")

        # Delete task
        # This covers task updates, task index updates, section pointers
        # updates, proper section pointer decrementing, and multiple section
        # processing
        parser, create = todo.create_parser(menu, ['test', '-d', "2"], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.delete(2)
        updated_file = self.update_file()
        assert updated_file == ['{"test": {"sections": [{"name": "sect1", "tasks": [1, 3]}, {"name": "sect2", "tasks": [2]}], "tasks": {"1": "task1", "2": "task3", "3": "task4"}, "check": []}}']

    def test_check(self):
        # ERROR: Nonexistent task
        parser, create = todo.create_parser(menu, ['test', '-c', 'notarealtask'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        with pytest.raises(SystemExit) as excinfo:
            test_todo.check('notarealtask')
        updated_file = self.update_file()
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'Task "notarealtask" does not exist.'

        # Successful
        parser, create = todo.create_parser(menu, ['test', '-c', 'task1'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.check('task1')
        updated_file = self.update_file()
        assert updated_file == ['{"test": {"sections": [{"name": "sect1", "tasks": [1]}], "tasks": {"1": "task1"}, "check": [1]}}']

        # ERROR: Already checked
        parser, create = todo.create_parser(menu, ['test', '-c', 'task1'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.check('task1')

        parser, create = todo.create_parser(menu, ['test', '-c', 'task1'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        with pytest.raises(SystemExit) as excinfo:
            test_todo.check('task1')
        updated_file = self.update_file()
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'Task "task1" is already checked.'

    def test_uncheck(self):
        # ERROR: Nonexistent task
        parser, create = todo.create_parser(menu, ['test', '-u', 'notarealtask'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        with pytest.raises(SystemExit) as excinfo:
            test_todo.uncheck('notarealtask')
        updated_file = self.update_file()
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'Task "notarealtask" does not exist.'

        # ERROR: Not checked
        parser, create = todo.create_parser(menu, ['test', '-u', 'task1'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        with pytest.raises(SystemExit) as excinfo:
            test_todo.uncheck('task1')
        updated_file = self.update_file()
        assert excinfo.type == SystemExit
        assert str(excinfo.value) == 'Task "task1" is not checked.'

        # Successful
        # The reason we're unchecking a task in the 2nd position is that I
        #   previously had the logic wrong to where it would sys.exit('already
        #   checked') if either the task wasn't in the check list or if the
        #   label wasn't the 1st one evaluated. Obviously that was a small fix
        #   but this test should still check for that just in case.
        parser, create = todo.create_parser(menu, ['test', '-a', 'task2'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.add('task2')
        parser, create = todo.create_parser(menu, ['test', '-c', 'task1'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.check('task1')
        parser, create = todo.create_parser(menu, ['test', '-c', 'task2'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.check('task2')

        parser, create = todo.create_parser(menu, ['test', '-u', 'task1'], TODO_FILE)
        test_todo = Todo(menu, parser, create, TODO_FILE)
        test_todo.uncheck('task1')
        updated_file = self.update_file()
        assert updated_file == ['{"test": {"sections": [{"name": "sect1", "tasks": [1]}], "tasks": {"1": "task1", "2": "task2"}, "check": [2]}}']


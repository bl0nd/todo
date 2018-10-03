# Todo Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## 0.1.3 (2018-09-26)
### Features
 - Tasks can be moved out of sections ([f9c71cd](https://github.com/bl0nd/todo/commit/f9c71cd))

### Modifications
 - Removed: find_project() ([e57f55b](https://github.com/bl0nd/todo/commit/e57f55b))
 - Updated: Project sections in .todo are now of the format: {"SectionName": [ID1, ID2, ...]} ([e57f55b](https://github.com/bl0nd/todo/commit/e57f55b))
 - Updated: Moving tasks is now done through the task ID ([377a9a2](https://github.com/bl0nd/todo/commit/377a9a2))
 
### Fixed
 - Moving nonexistent tasks is now handled ([2cf54aa](https://github.com/bl0nd/todo/commit/2cf54aa))
 - Moving tasks between sections within the same project no longer throws an "task exists" error ([b766299](https://github.com/bl0nd/todo/commit/b766299))


## 0.1.2 (2018-09-13)
### Features
 - Delete multiple tasks ([14a59b7](https://github.com/bl0nd/todo/commit/14a59b7))
 - Check/uncheck multiple tasks ([bdc9816](https://github.com/bl0nd/todo/commit/bdc9816))
 - Task numbers are shown on menu ([d013dca](https://github.com/bl0nd/todo/commit/d013dca))
### Modifications
 - Removed: init functionality (.todo is now included in repo) ([57c96ae](https://github.com/bl0nd/todo/commit/57c96ae))


## 0.1.1 (2018-09-06)
### Features
 - Project and section renaming ([965d39e](https://github.com/bl0nd/todo/commit/965d39e))
 - Ability to move tasks to different projects or sections ([a5cbd58](https://github.com/bl0nd/todo/commit/a5cbd58))

### Modifications
 - Added: nonexistent() to check for nonexistent project and section names ([00699db](https://github.com/bl0nd/todo/commit/00699db))
 - Added: unrecognized argument handling ([00699db](https://github.com/bl0nd/todo/commit/00699db))
 - Added: project name check helper function for tidier creating and renaming ([965d39e](https://github.com/bl0nd/todo/commit/965d39e))
  
### Fixed
 - Todo script now executes universally ([7c90b0a](https://github.com/bl0nd/todo/commit/7c90b0a))
 - section_delete() now iterates and deletes sections and tasks properly ([a5cbd58](https://github.com/bl0nd/todo/commit/a5cbd58))
 - section_delete() now updates check lists ([00699db](https://github.com/bl0nd/todo/commit/00699db))
 - get_updated_check() now doesn't immediately exit when archiving if the 1st project has no completed tasks, even though subsequent projects do ([00699db](https://github.com/bl0nd/todo/commit/00699db))


## 0.1.0 (2018-11-18)
 - Initial release
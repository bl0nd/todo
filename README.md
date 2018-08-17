# Todo
Todo is a simple and intuitive manager for TODO lists, allowing you to organize your life, or maybe just programming projects, from the terminal in a way that feels natural and looks stylish!

## Disclaimer
Before moving on, it wouldn't be fair of me to continue without mentioning and crediting the inspiration behind the project. Upon watching a completely unrelated video for better window switching in i3wm by the fantastic [Budlabs](https://www.youtube.com/channel/UCi8XrDg1bK_MJ0goOnbpTMQ) or [Nils Kvist](https://www.youtube.com/channel/UCi8XrDg1bK_MJ0goOnbpTMQ) (who, by the way, is a must-watch for anyone learning i3), I happened to notice this TODO list off to the side:

<p align="center">
  <img src="images/budlabs_todo.png">
</p>

I liked it so much that after failing to find any mention of it after listening to the video, reading the comments and his blog, and even scouring the AUR, I decided to make it.

Aside from some different colors, I kept the overall design essentially the same given the wonderful layout of the original. If you should come across this Nils Kvist and it becomes a problem, I compeltely understand and would have no problem making the necessary changes.

So thank you Budlabs for not only teaching me everything I now know about i3, but also for inspiring me to make something as functional and useful as a TODO list!

## Setup
### TODO Repository
Prior to usage, you must first initialize the Todo directory as a proper Todo repository:

```sh
$ todo init
```

This will create a *.todo* file which will store all data relevant to any projects, sections, or tasks you create.

### Alias
As an optional step, it is recommended that you create an alias to the script within *.bashrc*, *.bash_aliases*, or your respective shell configuration file. For example, if I installed the script to */opt/todo*, I could add the following line:

```diff
+ alias todo='python3 /opt/todo/todo.py'
```

## Usage
Todo has 4 main modes:
#### Normal

View or modify existing projects and sections.

```sh
$ todo [PROJECT [SECTION]]
```

##### Display
   - When executed with no arguments, Todo will display all existing projects, sections, and tasks:

<p align="center">
  <img src="images/todo_all.png">
</p>

   - However, when passed a project's or section's name, the output is adjusted to only show that specific project or section:

<p align="center">
  <img src="images/todo_specific.png">
</p>

##### Options
1. **Creation**
2. **Deletion**
3. **Archive**
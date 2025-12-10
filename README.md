# Playful-Minds

This project is an educational gaming application designed for children, featuring a variety of interactive games to enhance cognitive skills. Built using the **Flet** framework, it includes games like Edible Game, Color Smash, Number Dash, and more. The app supports user sessions, highscores, and push notifications, all managed through a SQLite database.

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Games](#games)
- [Services](#services)
- [Evaluation](#evaluation)
- [Results](#results)
- [Future Work](#future-work)
- [License](#license)

## Introduction
Playful Minds aims to make learning fun through engaging games that target different cognitive abilities such as pattern recognition, math skills, spelling, and more. The application is built with Flet for cross-platform compatibility and includes backend services for data management and user tracking.

## Features
- Interactive games for children
- User session management
- Highscore tracking
- Push notifications
- Database integration with SQLite
- Cross-platform support (Windows, macOS, Linux)

## Installation
To set up the project locally, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Playful-Minds.git
   cd Playful-Minds
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the application by executing the `main.py` file:
```bash
python main.py
```

The app will launch a window with the game menu. Select a game to start playing. Highscores and user data are stored locally in the database.

## Games
The following games are included in the application:
- **Edible Game**: Bite edible items while avoiding non-edible ones.
- **Color Smash**: Match colors in a fast-paced game.
- **Number Dash**: Run through numbers in a challenging dash.
- **Odd One Out**: Identify the odd item among similar ones.
- **Shape Sorter**: Sort shapes to boost visual skills.
- **Spell Drop**: Drop letters to form words correctly.
- **Maths Quest**: Solve challenging maths problems.
- **Word Builder**: Construct words from jumbled letters.

Each game is implemented as a separate Python module in the `games/` directory.

## Services
The application uses several services for functionality:
- **db.py**: Database operations using SQLite.
- **pages.py**: UI page management.
- **utils.py**: Utility functions.
- **push.py**: Push notification handling.
- **logs.py**: Event logging.
- **sessions.py**: User session management.

## Evaluation
The app's performance can be evaluated based on:
- **User Engagement**: Number of games played and time spent.
- **Highscores**: Top scores achieved in each game.
- **Feedback**: User reviews and bug reports.

## Results
Sample highscores (from `highscores.txt`):
- Edible Game: 1500 points
- Color Smash: 2000 points
- Number Dash: 1800 points

(Note: Actual results may vary based on user play.)

## Future Work
- **Additional Games**: Implement more educational games.
- **Multiplayer Mode**: Add online multiplayer features.
- **Analytics**: Integrate user analytics for better insights.
- **Mobile Support**: Optimize for mobile devices using Flet.
- **Web Version**: Develop a web-based version using Flask or similar.

## License

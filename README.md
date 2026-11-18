# Tamagotchi Simulator

A console-based virtual pet simulator written in C++. The application allows users to take care of a virtual pet by managing its health, hunger, energy, and mood.

## Features

- **Pet attributes:** Tracks four parameters: health, hunger, energy, and mood.
- **Interactive actions:** Feed, play with, let the pet sleep, and heal the pet.
- **Random events:** Generates events that can positively or negatively affect the pet's attributes.
- **Attribute management:** Includes checks for attribute limits and consequences when certain attributes reach critical values.
- **Visual status display:** Shows pet attributes using simple console-based status bars.
- **Input validation:** Checks that the pet's name contains at least one letter and handles invalid menu selections.

## Technical Concepts

- C++ functions and modular program structure
- References for modifying variables inside functions
- Conditional statements and loops
- Strings and basic string operations
- Random number generation using the C++ standard library
- Input handling and validation
- Constants and state management

## How to Run

Compile using a C++ compiler that supports C++11 or later:

```bash
g++ -std=c++11 main.cpp -o tamagotchi
```

Run the application:

```bash
./tamagotchi
```

On Windows, run:

```bash
tamagotchi.exe
```

## Usage

1. Enter a name for your virtual pet.
2. View its current attributes.
3. Choose an action from the menu:
   - `1` — Feed the pet
   - `2` — Play with the pet
   - `3` — Let the pet sleep
   - `4` — Heal the pet
   - `0` — Exit the game
4. Random events may occur after an action and affect the pet's attributes.

## Project Context

Developed as a personal C++ programming project to practise functions, references, state management, and basic interactive application logic.
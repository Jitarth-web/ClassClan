document.addEventListener('DOMContentLoaded', () => {
    const WORD_LENGTH = 5;
    const ROWS = 6;
    let currentRow = 0;
    let currentTile = 0;
    let isGameOver = false;
    let wordOfTheDay = '';
    let wordMeaning = '';

    // Initialize the game board immediately
    initializeGame();

    // Function to initialize the game
    function initializeGame() {
        setupGameBoard();
        setupKeyboardListeners();
        getWordOfTheDay();
        // Reset game state
        currentRow = 0;
        currentTile = 0;
        isGameOver = false;
    }

    // Function to set up the game board
    function setupGameBoard() {
        const gameBoard = document.getElementById('board');
        gameBoard.innerHTML = ''; // Clear existing board
        for (let i = 0; i < ROWS; i++) {
            const row = document.createElement('div');
            row.className = 'row';
            for (let j = 0; j < WORD_LENGTH; j++) {
                const tile = document.createElement('div');
                tile.className = 'tile';
                row.appendChild(tile);
            }
            gameBoard.appendChild(row);
        }
    }

    // Function to set up keyboard listeners
    function setupKeyboardListeners() {
        document.addEventListener('keydown', handleKeyPress);
        const keyboard = document.getElementById('keyboard');
        keyboard.querySelectorAll('button').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const key = button.getAttribute('data-key');
                handleInput(key);
            });
        });
    }

    function handleKeyPress(e) {
        if (isGameOver) return;
        
        const key = e.key.toUpperCase();
        if (key === 'BACKSPACE' || key === 'ENTER' || /^[A-Z]$/.test(key)) {
            handleInput(key);
        }
    }

    function handleInput(key) {
        if (isGameOver) return;

        if (key === 'BACKSPACE' && currentTile > 0) {
            deleteLetter();
        } else if (key === 'ENTER' && currentTile === WORD_LENGTH) {
            checkWord();
        } else if (currentTile < WORD_LENGTH && /^[A-Z]$/.test(key)) {
            addLetter(key);
        }
    }

    function addLetter(letter) {
        if (currentTile >= WORD_LENGTH) return;
        const tile = document.querySelector(`.row:nth-child(${currentRow + 1}) .tile:nth-child(${currentTile + 1})`);
        if (tile) {
            tile.textContent = letter;
            tile.classList.add('pop-in');
            currentTile++;
        }
    }

    function deleteLetter() {
        if (currentTile <= 0) return;
        currentTile--;
        const tile = document.querySelector(`.row:nth-child(${currentRow + 1}) .tile:nth-child(${currentTile + 1})`);
        if (tile) {
            tile.textContent = '';
            tile.classList.remove('pop-in');
        }
    }

    async function checkWord() {
        if (currentRow >= ROWS) return;
        
        const row = document.querySelector(`.row:nth-child(${currentRow + 1})`);
        if (!row) return;
        
        const guess = Array.from(row.children).map(tile => tile.textContent).join('');
        
        // First validate if the word exists
        const isValid = await isValidWord(guess);
        if (!isValid) {
            row.classList.add('shake');
            setTimeout(() => row.classList.remove('shake'), 500);
            showMessage('Not a valid word!');
            currentTile = 0;  // Reset currentTile when word is invalid
            return;
        }

        // Update tiles and check game status
        updateTiles(row, guess);

        // Wait for animations to complete before showing game end states
        const animationDelay = 250 * WORD_LENGTH + 100; // 250ms per tile plus extra buffer

        // Check if game is won
        if (guess === wordOfTheDay) {
            setTimeout(() => {
                isGameOver = true;
                showMessage('Magnificent!');
                setTimeout(showMeaningModal, 1000);
            }, animationDelay);
            return;
        }

        // Check if this was the last row before moving to next row
        if (currentRow === ROWS - 1) {
            setTimeout(() => {
                isGameOver = true;
                showMessage('Game Over! The word was: ' + wordOfTheDay);
                setTimeout(showMeaningModal, 1000);
            }, animationDelay);
            return;
        }

        // Move to next row if game is not over
        currentRow++;
        currentTile = 0;
    }

    // Function to check if a word has unique characters
    function hasUniqueCharacters(word) {
        return new Set(word.toLowerCase()).size === word.length;
    }

    // Function to get word meaning from the API
    async function getWordMeaning(word) {
        try {
            const response = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${word}`);
            const data = await response.json();
            
            if (data && data[0] && data[0].meanings) {
                const meanings = data[0].meanings;
                let meaningText = '';
                
                meanings.forEach((meaning, index) => {
                    meaningText += `<p><strong>${meaning.partOfSpeech}</strong>: `;
                    if (meaning.definitions && meaning.definitions[0]) {
                        meaningText += `${meaning.definitions[0].definition}</p>`;
                        if (meaning.definitions[0].example) {
                            meaningText += `<p><em>Example: ${meaning.definitions[0].example}</em></p>`;
                        }
                    }
                });
                
                return meaningText;
            }
            return 'Meaning not found.';
        } catch (error) {
            console.error('Error fetching word meaning:', error);
            return 'Unable to fetch word meaning.';
        }
    }

    // Function to show the meaning modal
    function showMeaningModal() {
        const modal = document.getElementById('meaning-modal');
        const modalWord = document.getElementById('modal-word');
        const wordMeaningDiv = document.getElementById('word-meaning');
        
        modalWord.textContent = wordOfTheDay;
        wordMeaningDiv.innerHTML = wordMeaning;
        modal.style.display = 'block';
    }

    // Close modal when clicking the close button
    document.getElementById('close-modal').addEventListener('click', () => {
        document.getElementById('meaning-modal').style.display = 'none';
    });

    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        const modal = document.getElementById('meaning-modal');
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Function to get a random 5-letter word from the API
    async function getRandomWord() {
        try {
            const response = await fetch('https://random-word-api.herokuapp.com/word?length=5');
            const words = await response.json();
            const word = words[0].toUpperCase();
            
            // Validate the word using Free Dictionary API
            const validationResponse = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${word}`);
            
            if (validationResponse.ok && hasUniqueCharacters(word)) {
                // Get and store the word meaning
                wordMeaning = await getWordMeaning(word);
                return word;
            }
            return getRandomWord(); // Try again if word isn't valid or has duplicate letters
        } catch (error) {
            console.error('Error fetching word:', error);
            wordMeaning = 'A cognitive activity; the act of using the mind to produce thoughts.';
            return 'THINK'; // Fallback word
        }
    }

    // Async function to get and set word of the day
    async function getWordOfTheDay() {
        try {
            wordOfTheDay = await getRandomWord();
            console.log("Word of the day:", wordOfTheDay);
        } catch (error) {
            console.error('Error setting word of the day:', error);
            wordOfTheDay = 'THINK'; // Fallback word
        }
    }

    function updateTiles(row, guess) {
        const tiles = Array.from(row.children);
        const remainingLetters = wordOfTheDay.split('');
        const keyboardButtons = {};
        document.querySelectorAll('#keyboard button').forEach(button => {
            keyboardButtons[button.getAttribute('data-key')] = button;
        });

        // First pass: mark correct letters
        tiles.forEach((tile, index) => {
            const letter = tile.textContent;
            if (letter === wordOfTheDay[index]) {
                tile.classList.add('correct');
                remainingLetters[index] = null;
                // Update keyboard
                const keyButton = keyboardButtons[letter];
                if (keyButton) {
                    keyButton.className = 'correct'; // Reset classes and add correct
                }
            }
        });

        // Second pass: mark present letters
        tiles.forEach((tile, index) => {
            if (tile.classList.contains('correct')) return;

            const letter = tile.textContent;
            const letterPosition = remainingLetters.indexOf(letter);

            if (letterPosition !== -1) {
                tile.classList.add('present');
                remainingLetters[letterPosition] = null;
                // Update keyboard if not already correct
                const keyButton = keyboardButtons[letter];
                if (keyButton && !keyButton.classList.contains('correct')) {
                    keyButton.className = 'present';
                }
            } else {
                tile.classList.add('absent');
                // Update keyboard if not already correct or present
                const keyButton = keyboardButtons[letter];
                if (keyButton && 
                    !keyButton.classList.contains('correct') && 
                    !keyButton.classList.contains('present')) {
                    keyButton.className = 'absent';
                }
            }
        });

        // Add flip animation to all tiles
        tiles.forEach((tile, index) => {
            setTimeout(() => {
                tile.classList.add('flip');
            }, index * 250);
        });
    }

    // Function to validate if a word exists in the dictionary
    async function isValidWord(word) {
        try {
            const response = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${word.toLowerCase()}`);
            return response.ok;
        } catch (error) {
            console.error('Error validating word:', error);
            return false;
        }
    }

    // Function to show message to user
    function showMessage(message) {
        const existingMessage = document.querySelector('.message');
        if (existingMessage) {
            existingMessage.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message';
        messageDiv.textContent = message;
        document.body.appendChild(messageDiv);

        // Add show class after a small delay to trigger animation
        setTimeout(() => {
            messageDiv.classList.add('show');
            // Remove message after 2 seconds
            setTimeout(() => {
                messageDiv.classList.remove('show');
                setTimeout(() => messageDiv.remove(), 300);
            }, 2000);
        }, 10);
    }
});
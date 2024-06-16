require('dotenv').config();
const express = require('express');
const { Sequelize } = require('sequelize');
const bodyParser = require('body-parser');
const cors = require('cors');

const app = express();
const port = 3000;

// Middleware
app.use(bodyParser.json());
app.use(cors());

// Set up Sequelize
const { sequelize, User, Card, Deck, DeckCard } = require('./models');

// Test database connection and sync models
sequelize.authenticate()
  .then(() => {
    console.log('Database connected...');
    return sequelize.sync({ alter: true }); // Sync all defined models to the DB and alter existing tables if necessary
  })
  .then(() => console.log('Database synced...'))
  .catch(err => console.log('Error: ' + err));

// Basic route
app.get('/', (req, res) => res.send('SpoilsOnline API'));

// Routes
const users = require('./routes/users');
const cards = require('./routes/cards');
const decks = require('./routes/decks');

app.use('/api/users', users);
app.use('/api/cards', cards);
app.use('/api/decks', decks);

// Start server
app.listen(port, () => console.log(`Server running on port ${port}`));


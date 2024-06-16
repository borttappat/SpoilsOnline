const express = require('express');
const router = express.Router();
const { Deck } = require('../models');

// Get all decks
router.get('/', async (req, res) => {
  try {
    const decks = await Deck.findAll();
    console.log('Fetched decks:', decks); // Log fetched decks
    res.json(decks);
  } catch (err) {
    console.error('Error fetching decks:', err);
    res.status(500).json({ error: err.message });
  }
});

// Create a new deck
router.post('/', async (req, res) => {
  try {
    console.log('Create deck request body:', req.body); // Log request body
    const newDeck = await Deck.create(req.body);
    console.log('Created deck:', newDeck); // Log created deck
    res.json(newDeck);
  } catch (err) {
    console.error('Error creating deck:', err);
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;


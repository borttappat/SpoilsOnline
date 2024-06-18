const express = require('express');
const router = express.Router();
const { Card } = require('../models');

// Get all cards
router.get('/', async (req, res) => {
  try {
    const cards = await Card.findAll();
    res.json(cards);
  } catch (err) {
    console.error('Error fetching cards:', err);
    res.status(500).json({ error: err.message });
  }
});

// Create a new card
router.post('/', async (req, res) => {
  try {
    console.log('Create card request body:', req.body); // Log request body
    const newCard = await Card.create(req.body);
    console.log('Created card:', newCard); // Log created card
    res.json(newCard);
  } catch (err) {
    console.error('Error creating card:', err);
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;


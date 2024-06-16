const express = require('express');
const router = express.Router();
const { Card } = require('../models');

// Get all cards
router.get('/', async (req, res) => {
  try {
    const cards = await Card.findAll();
    res.json(cards);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Create a new card
router.post('/', async (req, res) => {
  try {
    const newCard = await Card.create(req.body);
    res.json(newCard);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;


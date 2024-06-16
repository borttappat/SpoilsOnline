const express = require('express');
const router = express.Router();
const { User } = require('../models');

// Get all users
router.get('/', async (req, res) => {
  try {
    const users = await User.findAll();
    console.log('Fetched users:', users); // Log fetched users
    res.json(users);
  } catch (err) {
    console.error('Error fetching users:', err); // Log error
    res.status(500).json({ error: err.message });
  }
});

// Create a new user
router.post('/', async (req, res) => {
  try {
    const newUser = await User.create(req.body);
    res.json(newUser);
  } catch (err) {
    console.error('Error creating user:', err); // Log error
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;


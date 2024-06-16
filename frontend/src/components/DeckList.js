import React, { useState, useEffect } from 'react';
import { getDecks, createDeck } from '../services/api';

const DeckList = () => {
  const [decks, setDecks] = useState([]);
  const [name, setName] = useState('');
  const [userId, setUserId] = useState('');

  useEffect(() => {
    const fetchDecks = async () => {
      try {
        const decks = await getDecks();
        console.log('Fetched decks:', decks); // Log fetched decks
        setDecks(decks);
      } catch (error) {
        console.error('Error fetching decks:', error); // Log error
      }
    };

    fetchDecks();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const newDeck = await createDeck({ userId: parseInt(userId, 10), name });
      console.log('Created deck:', newDeck); // Log created deck
      setDecks([...decks, newDeck]);
      setName('');
      setUserId('');
    } catch (error) {
      console.error('Error creating deck:', error); // Log error
    }
  };

  return (
    <div>
      <h2>Decks</h2>
      <ul>
        {decks.map((deck) => (
          <li key={deck.id}>{deck.name}</li>
        ))}
      </ul>
      <h2>Add Deck</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit">Add Deck</button>
      </form>
    </div>
  );
};

export default DeckList;


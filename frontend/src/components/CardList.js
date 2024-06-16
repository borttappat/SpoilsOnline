import React, { useState, useEffect } from 'react';
import { getCards, createCard } from '../services/api';

const CardList = () => {
  const [cards, setCards] = useState([]);
  const [name, setName] = useState('');
  const [strength, setStrength] = useState('');
  const [speed, setSpeed] = useState('');
  const [life, setLife] = useState('');
  const [threshold, setThreshold] = useState('');
  const [cost, setCost] = useState('');
  const [extraCost, setExtraCost] = useState('');
  const [description, setDescription] = useState('');
  const [flipUp, setFlipUp] = useState('');
  const [flipUpThreshold, setFlipUpThreshold] = useState('');

  useEffect(() => {
    const fetchCards = async () => {
      const cards = await getCards();
      setCards(cards);
    };

    fetchCards();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newCard = await createCard({ name, strength, speed, life, threshold, cost, extra_cost: extraCost, description, flip_up: flipUp, flip_up_threshold: flipUpThreshold });
    setCards([...cards, newCard]);
    setName('');
    setStrength('');
    setSpeed('');
    setLife('');
    setThreshold('');
    setCost('');
    setExtraCost('');
    setDescription('');
    setFlipUp('');
    setFlipUpThreshold('');
  };

  return (
    <div>
      <h2>Cards</h2>
      <ul>
        {cards.map((card) => (
          <li key={card.id}>{card.name}</li>
        ))}
      </ul>
      <h2>Add Card</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          type="number"
          placeholder="Strength"
          value={strength}
          onChange={(e) => setStrength(e.target.value)}
          required
        />
        <input
          type="number"
          placeholder="Speed"
          value={speed}
          onChange={(e) => setSpeed(e.target.value)}
          required
        />
        <input
          type="number"
          placeholder="Life"
          value={life}
          onChange={(e) => setLife(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Threshold"
          value={threshold}
          onChange={(e) => setThreshold(e.target.value)}
        />
        <input
          type="number"
          placeholder="Cost"
          value={cost}
          onChange={(e) => setCost(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Extra Cost"
          value={extraCost}
          onChange={(e) => setExtraCost(e.target.value)}
        />
        <input
          type="text"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <input
          type="number"
          placeholder="Flip Up"
          value={flipUp}
          onChange={(e) => setFlipUp(e.target.value)}
        />
        <input
          type="text"
          placeholder="Flip Up Threshold"
          value={flipUpThreshold}
          onChange={(e) => setFlipUpThreshold(e.target.value)}
        />
        <button type="submit">Add Card</button>
      </form>
    </div>
  );
};

export default CardList;


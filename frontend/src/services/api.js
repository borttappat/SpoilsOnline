import axios from 'axios';

const API_URL = 'http://localhost:3000/api'; // Ensure this matches your backend URL

export const getUsers = async () => {
  try {
    const response = await axios.get(`${API_URL}/users`);
    console.log('Fetched users:', response.data); // Log fetched users
    return response.data;
  } catch (error) {
    console.error('Error fetching users:', error); // Log error
    throw error;
  }
};

export const createUser = async (user) => {
  const response = await axios.post(`${API_URL}/users`, user);
  return response.data;
};

export const getCards = async () => {
  const response = await axios.get(`${API_URL}/cards`);
  return response.data;
};

export const createCard = async (card) => {
  const response = await axios.post(`${API_URL}/cards`, card);
  return response.data;
};

export const getDecks = async () => {
  const response = await axios.get(`${API_URL}/decks`);
  return response.data;
};

export const createDeck = async (deck) => {
  const response = await axios.post(`${API_URL}/decks`, deck);
  return response.data;
};


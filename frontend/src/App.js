import React from 'react';
import UserList from './components/UserList';
import CardList from './components/CardList';
import DeckList from './components/DeckList';

const App = () => {
  return (
    <div>
      <h1>SpoilsOnline</h1>
      <UserList />
      <CardList />
      <DeckList />
    </div>
  );
};

export default App;


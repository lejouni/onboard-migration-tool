import { render, screen } from '@testing-library/react';
import App from './App';

test('renders backend web ui heading', () => {
  render(<App />);
  const linkElement = screen.getByText(/Backend Web UI/i);
  expect(linkElement).toBeInTheDocument();
});
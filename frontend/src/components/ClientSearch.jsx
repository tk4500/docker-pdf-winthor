import React, { useState, useEffect, useRef } from 'react';
import api from '../api';
import { Search, Loader } from 'lucide-react';

export default function ClientSearch({ onSelect, initialValue }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  
  const inputRef = useRef(null);
  const listRef = useRef(null);

  useEffect(() => {
    if (initialValue) setQuery(initialValue);
  }, [initialValue]);

  const handleSearch = async (termo) => {
    setQuery(termo);
    setFocusedIndex(-1);
    if (termo.length < 3) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.get(`/clientes/busca?termo=${termo.replaceAll("%", "%25")}`);
      setResults(data);
      setShowDropdown(true);
    } catch (error) { console.error(error); } finally { setLoading(false); }
  };

  const selectClient = (cli) => {
    setQuery(`${cli.id} - ${cli.razao_social}`);
    setShowDropdown(false);
    onSelect(cli);
    // Pula para o número do pedido
    setTimeout(() => document.getElementById('num-pedido-input')?.focus(), 100);
  };

  const handleKeyDown = (e) => {
    if (!showDropdown || results.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIndex(prev => (prev < results.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex(prev => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      const target = focusedIndex >= 0 ? results[focusedIndex] : results[0];
      if (target) selectClient(target);
    }
  };

  return (
    <div className="relative w-full">
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => query.length >= 3 && setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          placeholder="Digite razão social, CNPJ ou ID..."
          className="w-full pl-8 pr-2 py-2 text-sm border rounded focus:ring-2 focus:ring-blue-500 outline-none"
        />
        <div className="absolute left-2 top-2.5 text-gray-400">
          {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        </div>
      </div>
      {showDropdown && results.length > 0 && (
        <ul ref={listRef} className="absolute z-[9999] w-full bg-white border border-gray-300 mt-1 rounded shadow-lg max-h-60 overflow-y-auto">
          {results.map((cli, idx) => (
            <li key={cli.id} onClick={() => selectClient(cli)}
              className={`px-4 py-2 cursor-pointer text-sm border-b last:border-0 ${focusedIndex === idx ? 'bg-blue-100 font-bold' : 'hover:bg-blue-50'}`}>
              <span className="font-bold">{cli.id}</span> - {cli.razao_social}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
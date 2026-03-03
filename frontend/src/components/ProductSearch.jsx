import React, { useState, useEffect, useRef } from 'react';
import api from '../api';
import { Search, Loader } from 'lucide-react';

export default function ProductSearch({ onSelect, autoFocus, rowIndex }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  
  const inputRef = useRef(null);

  useEffect(() => {
    if (autoFocus) {
      // Pequeno delay para garantir que o DOM renderizou a nova linha
      const timer = setTimeout(() => inputRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    }
  }, [autoFocus]);

  const handleSearch = async (termo) => {
    setQuery(termo);
    setFocusedIndex(-1);
    if (termo.length < 3) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.get(`/produtos/busca?termo=${termo.replaceAll("%", "%25")}`);
      setResults(data);
      setShowDropdown(true);
    } catch (error) { console.error(error); } finally { setLoading(false); }
  };

  const selectProduct = (prod) => {
    setQuery(`${prod.id} - ${prod.nome}`);
    setShowDropdown(false);
    onSelect(prod);
    // Pula para a Quantidade da mesma linha
    setTimeout(() => {
      const el = document.getElementById(`qtd-input-${rowIndex}`);
      if (el) { el.focus(); el.select(); }
    }, 50);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown' && results.length > 0) {
      e.preventDefault();
      setShowDropdown(true);
      setFocusedIndex(prev => (prev < results.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex(prev => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      if (showDropdown && results.length > 0) {
        e.preventDefault();
        const target = focusedIndex >= 0 ? results[focusedIndex] : results[0];
        if (target) selectProduct(target);
      }
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
          className="w-full pl-8 pr-2 py-1 text-sm border rounded focus:ring-2 focus:ring-blue-500 outline-none"
          placeholder="Produto..."
        />
        <div className="absolute left-2 top-1.5 text-gray-400">
          {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        </div>
      </div>
      {showDropdown && results.length > 0 && (
        <ul className="absolute z-[9999] w-full bg-white border border-gray-300 mt-1 rounded shadow-2xl max-h-60 overflow-y-auto">
          {results.map((prod, idx) => (
            <li key={prod.id} onClick={() => selectProduct(prod)}
              className={`px-4 py-2 cursor-pointer text-sm border-b last:border-0 ${focusedIndex === idx ? 'bg-blue-100 font-bold' : 'hover:bg-blue-50'}`}>
              {prod.id} - {prod.nome}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
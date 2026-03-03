import React, { useState, useEffect, useRef } from 'react';
import api from '../api';
import { Search, Loader } from 'lucide-react';

export default function ProductSearch({ onSelect, initialValue, autoFocus, rowIndex }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  
  // --- Controles de Teclado ---
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  // Auto-foco ao criar nova linha
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  // Se o initialValue mudar (edição)
  useEffect(() => {
    if (initialValue) setQuery(initialValue);
  }, [initialValue]);

  // Rola o dropdown automaticamente quando usa a seta pra baixo/cima
  useEffect(() => {
    if (focusedIndex >= 0 && listRef.current) {
      const activeItem = listRef.current.children[focusedIndex];
      if (activeItem) {
        activeItem.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [focusedIndex]);

  const handleSearch = async (termo) => {
    setQuery(termo);
    setFocusedIndex(-1); // Reseta o foco ao digitar

    if (termo.length < 3) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const { data } = await api.get(`/produtos/busca?termo=${termo.replaceAll("%", "%25")}`);
      setResults(data);
      setShowDropdown(true);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const selectProduct = (prod) => {
    setQuery(`${prod.id} - ${prod.nome}`);
    setShowDropdown(false);
    setFocusedIndex(-1);
    onSelect(prod);

    // Pula para o campo de Quantidade automaticamente!
    setTimeout(() => {
      const qtdInput = document.getElementById(`qtd-input-${rowIndex}`);
      if (qtdInput) qtdInput.focus();
    }, 100);
  };

  const handleKeyDown = (e) => {
    if (!showDropdown || results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex((prev) => (prev > 0 ? prev - 1 : 0));
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      if (focusedIndex >= 0) {
        selectProduct(results[focusedIndex]); // Pega o item destacado
      } else if (results.length > 0) {
        selectProduct(results[0]); // Pega o primeiro se não destacou nenhum
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
          placeholder="Digite cód ou nome..."
          className="w-full pl-8 pr-2 py-1 text-sm border rounded focus:ring-2 focus:ring-blue-500 outline-none"
        />
        <div className="absolute left-2 top-1.5 text-gray-400">
          {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        </div>
      </div>

      {showDropdown && results.length > 0 && (
        <ul 
          ref={listRef}
          className="absolute !z-[9999] w-full bg-white border border-gray-300 mt-1 rounded shadow-2xl max-h-60 overflow-y-auto"
        >
          {results.map((prod, idx) => (
            <li
              key={prod.id}
              onClick={() => selectProduct(prod)}
              className={`px-4 py-2 cursor-pointer text-sm border-b last:border-0 
                ${focusedIndex === idx ? 'bg-blue-100 font-bold' : 'hover:bg-blue-50'}`}
            >
              <span className="text-gray-800">{prod.id}</span> - {prod.nome} 
              <span className="block text-xs text-gray-500">EAN: {prod.ean} | Un: {prod.unidade}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
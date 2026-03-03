import React, { useState, useEffect } from 'react';
import api from '../api';
import { Search, Loader } from 'lucide-react';

export default function ClientSearch({ onSelect, initialValue }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    if (initialValue) setQuery(initialValue);
  }, [initialValue]);

  const handleSearch = async (termo) => {
    setQuery(termo);
    if (termo.length < 3) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {

      const { data } = await api.get(`/clientes/busca?termo=${termo.replaceAll("%", "%25")}`);
      setResults(data);
      setShowDropdown(true);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const selectClient = (cli) => {
    setQuery(`${cli.id} - ${cli.razao_social}`);
    setShowDropdown(false);
    onSelect(cli);
  };

  return (
    <div className="relative w-full">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
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
        <ul className="absolute z-50 w-full bg-white border border-gray-300 mt-1 rounded shadow-lg max-h-60 overflow-y-auto">
          {results.map((cli) => (
            <li
              key={cli.id}
              onClick={() => selectClient(cli)}
              className="px-4 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b last:border-0"
            >
              <span className="font-bold text-gray-700">{cli.id}</span> - {cli.razao_social}
              <span className="block text-xs text-gray-500">CNPJ: {cli.cnpj_cpf}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
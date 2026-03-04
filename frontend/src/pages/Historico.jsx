import React, { useEffect, useState } from 'react';
import api from '../api';
import { Search, Filter, Calendar, FileText, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Historico() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filtros, setFiltros] = useState({
    status: '',
    origem: '' // PDF ou MANUAL
  });
  const navigate = useNavigate();

  const fetchHistorico = async () => {
    setLoading(true);
    try {
      // Usamos o endpoint list-advanced que já criamos
      const { data } = await api.post('/pedidos/list-advanced', {
        status: filtros.status || null,
        // Caso queira adicionar filtro de origem no backend depois:
        // origem: filtros.origem || null 
      });
      setJobs(data.items);
    } catch (error) {
      console.error("Erro ao buscar histórico:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistorico();
  }, [filtros]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
        <FileText className="mr-2 text-blue-600" /> Consulta de Pedidos
      </h1>

      {/* Barra de Filtros */}
      <div className="bg-white p-4 rounded-lg shadow mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Status</label>
          <select 
            className="w-full border rounded p-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            value={filtros.status}
            onChange={(e) => setFiltros({...filtros, status: e.target.value})}
          >
            <option value="">Todos os Status</option>
            <option value="ENVIADO_WINTHOR">Enviado ao Winthor</option>
            <option value="CANCELADO">Cancelado</option>
            <option value="ERRO">Erro de Processamento</option>
            <option value="AGUARDANDO_APROVACAO">Aguardando Aprovação</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Origem</label>
          <select 
            className="w-full border rounded p-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            value={filtros.origem}
            onChange={(e) => setFiltros({...filtros, origem: e.target.value})}
          >
            <option value="">Todas as Origens</option>
            <option value="PDF">Arquivo PDF</option>
            <option value="MANUAL">Digitação Manual</option>
          </select>
        </div>

        <div className="flex items-end">
          <button 
            onClick={fetchHistorico}
            className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700 transition-colors flex justify-center items-center font-bold"
          >
            <Search className="w-4 h-4 mr-2" /> Filtrar
          </button>
        </div>
      </div>

      {/* Lista de Resultados */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">Data</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">Arquivo/Ref</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">Winthor ID</th>
              <th className="px-6 py-3 text-center"></th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr><td colSpan="5" className="p-10 text-center text-gray-500">Buscando registros...</td></tr>
            ) : jobs.length === 0 ? (
              <tr><td colSpan="5" className="p-10 text-center text-gray-500">Nenhum pedido encontrado com estes filtros.</td></tr>
            ) : (
              jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {new Date(job.data_criacao).toLocaleString('pt-BR')}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm font-bold text-gray-900">{job.nome_arquivo}</div>
                    <div className="text-xs text-gray-400">ID: {job.id.substring(0,8)}...</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${
                      job.status_global === 'ENVIADO_WINTHOR' ? 'bg-green-100 text-green-700' :
                      job.status_global === 'CANCELADO' ? 'bg-gray-100 text-gray-600' : 'bg-red-100 text-red-700'
                    }`}>
                      {job.status_global}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-mono text-blue-600">
                    {job.winthor_order_id || '---'}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <button 
                      onClick={() => navigate(`/pedido/${job.id}`)}
                      className="text-gray-400 hover:text-blue-600"
                    >
                      <ChevronRight />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
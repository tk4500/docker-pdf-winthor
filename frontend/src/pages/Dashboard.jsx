import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { FileText, LogOut, RefreshCw, AlertCircle, Plus, Trash2 } from 'lucide-react';
import { Plus } from "lucide-react";

export default function Dashboard() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const username = localStorage.getItem("username");
  const role = localStorage.getItem("role");

  const fetchJobs = async () => {
    setLoading(true);
    try {
      // Busca todos os pedidos. O backend vai filtrar pelo usuário logado automaticamente.
      const response = await api.post("/pedidos/list-advanced?limit=200", {});

      // Filtra no frontend para não mostrar os já finalizados ou cancelados
      const unfinishedJobs = response.data.items.filter(
        (job) =>
          job.status_global !== "ENVIADO_WINTHOR" &&
          job.status_global !== "CANCELADO" &&
          job.status_global !== "MULTIPLOS_PEDIDOS_DETECTADOS",
      );

      setJobs(unfinishedJobs);
    } catch (error) {
      console.error("Erro ao buscar pedidos:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/login");
  };

  // Função auxiliar para cores de status
  const getStatusColor = (status) => {
    if (status.includes("ERRO")) return "bg-red-100 text-red-800";
    if (status === "AGUARDANDO_APROVACAO")
      return "bg-yellow-100 text-yellow-800";
    if (status === "VALIDADO") return "bg-green-100 text-green-800";
    return "bg-blue-100 text-blue-800"; // Pendente, processando, etc
  };

  const handleCancelJob = async (e, jobId) => {
    e.stopPropagation(); // Evita que clique no botão abra a tela de edição do pedido

    if (!window.confirm("Tem certeza que deseja CANCELAR este pedido? Ele não será enviado ao Winthor.")) {
      return;
    }

    try {
      await api.delete(`/pedidos/${jobId}`);
      // Atualiza a lista automaticamente após cancelar
      fetchJobs();
    } catch (error) {
      alert("Erro ao cancelar o pedido: " + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navbar Superior */}
      <nav className="bg-white shadow-sm px-6 py-4 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <FileText className="text-blue-600 w-6 h-6" />
          <h1 className="text-xl font-bold text-gray-800">
            Winthor PDF Parser
          </h1>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-600">
            Olá, <strong>{username}</strong> ({role})
          </span>
          <button
            onClick={handleLogout}
            className="text-gray-500 hover:text-red-600 flex items-center text-sm"
          >
            <LogOut className="w-4 h-4 mr-1" /> Sair
          </button>
        </div>
      </nav>

      {/* Conteúdo Principal */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold text-gray-800">
            Pedidos em Andamento
          </h2>

          <div className="flex space-x-2">
            <button
              onClick={() => navigate("/upload")} // <--- Botão Novo
              className="bg-blue-600 text-white px-4 py-2 rounded-md shadow hover:bg-blue-700 flex items-center"
            >
              <Plus className="w-4 h-4 mr-2" /> Novo Pedido
            </button>

            <button onClick={fetchJobs} className="...">
              ...
            </button>
          </div>
        </div>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold text-gray-800">
            Pedidos em Andamento
          </h2>
          <button
            onClick={fetchJobs}
            className="bg-white border border-gray-300 px-3 py-2 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center"
          >
            <RefreshCw
              className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`}
            />
            Atualizar
          </button>
        </div>

        {/* Tabela de Pedidos */}
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          {loading && jobs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              Carregando pedidos...
            </div>
          ) : jobs.length === 0 ? (
            <div className="p-8 text-center text-gray-500 flex flex-col items-center">
              <AlertCircle className="w-8 h-8 text-gray-400 mb-2" />
              Nenhum pedido pendente de ação no momento.
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {jobs.map((job) => (
                <li key={job.id} onClick={() => navigate(`/pedido/${job.id}`)}>
                  <div className="px-4 py-4 sm:px-6 hover:bg-gray-50 transition-colors cursor-pointer">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-blue-600 truncate">
                        {job.nome_arquivo}
                      </p>
                      <div className="ml-2 flex-shrink-0 flex">
                        <p
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(job.status_global)}`}
                        >
                          {job.status_global.replace(/_/g, " ")}
                        </p>
                        <div className="ml-2 flex-shrink-0 flex">
                          <p className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(job.status_global)}`}>
                            {job.status_global.replace(/_/g, ' ')}
                          </p>

                          {/* Botão de Cancelar */}
                          <button
                            onClick={(e) => handleCancelJob(e, job.id)}
                            className="ml-4 text-red-400 hover:text-red-600 transition-colors"
                            title="Cancelar Pedido"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    </div>
                    <div className="mt-2 sm:flex sm:justify-between">
                      <div className="sm:flex">
                        <p className="flex items-center text-sm text-gray-500">
                          Origem: {job.origem_entrada}
                        </p>
                      </div>
                      <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                        <p>
                          Criado em:{" "}
                          {new Date(job.data_criacao).toLocaleString("pt-BR")}
                        </p>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { UploadCloud, CheckCircle, AlertTriangle, FileType } from 'lucide-react';

export default function Upload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [options, setOptions] = useState({
    auto_process: false,
    is_bonificacao: false,
    force_ai: false
  });
  const navigate = useNavigate();

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    // Adiciona as opções
    formData.append('auto_process', options.auto_process);
    formData.append('is_bonificacao', options.is_bonificacao);
    formData.append('force_ai', options.force_ai);

    try {
      const response = await api.post('/pedidos/upload-async', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      // Sucesso: Redireciona para o dashboard ou direto para o pedido
      // Vamos para o dashboard para ver ele processando
      navigate('/');
    } catch (error) {
      alert('Erro ao enviar arquivo: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
        <UploadCloud className="mr-2" /> Novo Pedido
      </h2>

      <div className="bg-white p-8 rounded-lg shadow-md">
        <form onSubmit={handleUpload} className="space-y-6">
          
          {/* Área de Seleção de Arquivo */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-10 text-center hover:bg-gray-50 transition-colors relative">
            <input 
              type="file" 
              accept=".pdf,.json" 
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            {file ? (
              <div className="text-blue-600 font-medium flex flex-col items-center">
                <FileType className="w-12 h-12 mb-2" />
                <span>{file.name}</span>
                <span className="text-xs text-gray-400 mt-1">Clique para alterar</span>
              </div>
            ) : (
              <div className="text-gray-500 flex flex-col items-center">
                <UploadCloud className="w-12 h-12 mb-2 text-gray-300" />
                <span className="font-medium">Clique ou arraste um PDF aqui</span>
                <span className="text-xs mt-1">Suporta arquivos PDF ou JSON</span>
              </div>
            )}
          </div>

          {/* Opções */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="flex items-center space-x-3 p-3 border rounded cursor-pointer hover:bg-gray-50">
              <input 
                type="checkbox" 
                checked={options.is_bonificacao}
                onChange={e => setOptions({...options, is_bonificacao: e.target.checked})}
                className="h-5 w-5 text-blue-600 rounded"
              />
              <span className="text-sm font-medium">É Bonificação?</span>
            </label>

            <label className="flex items-center space-x-3 p-3 border rounded cursor-pointer hover:bg-gray-50">
              <input 
                type="checkbox" 
                checked={options.force_ai}
                onChange={e => setOptions({...options, force_ai: e.target.checked})}
                className="h-5 w-5 text-blue-600 rounded"
              />
              <span className="text-sm font-medium">Forçar uso de IA</span>
            </label>

            <label className="flex items-center space-x-3 p-3 border rounded cursor-pointer hover:bg-gray-50">
              <input 
                type="checkbox" 
                checked={options.auto_process}
                onChange={e => setOptions({...options, auto_process: e.target.checked})}
                className="h-5 w-5 text-blue-600 rounded"
              />
              <span className="text-sm font-medium">Processar Automaticamente</span>
            </label>
          </div>

          {/* Botão de Envio */}
          <button
            type="submit"
            disabled={!file || uploading}
            className={`w-full py-3 px-4 rounded-md text-white font-bold transition-all
              ${!file || uploading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 shadow-lg'}
            `}
          >
            {uploading ? 'Enviando e Processando...' : 'Iniciar Processamento'}
          </button>
        </form>
      </div>
    </div>
  );
}
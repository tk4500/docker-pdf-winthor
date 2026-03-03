import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import ClientSearch from '../components/ClientSearch';
import ProductSearch from '../components/ProductSearch';
import { Save, ArrowLeft, Plus, Trash2, ShoppingCart } from 'lucide-react';

export default function PedidoManual() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  
  // Estado Principal do Pedido Manual
  const [pedido, setPedido] = useState({
    cliente: null,
    itens: [],
    options: {
      auto_process: true, // Manual já vai processar direto
      is_bonificacao: false
    }
  });

  // Atualiza o Cliente
  const handleClientSelect = (cliWinthor) => {
    setPedido({ ...pedido, cliente: cliWinthor });
  };

  // Adiciona linha vazia na tabela
  const addNewItem = () => {
    if (!pedido.cliente) {
      alert("Selecione um cliente primeiro para podermos buscar os preços corretos da região.");
      return;
    }

    const newItem = {
      id: Date.now(), // ID temporário pro React (key)
      produto: null,
      quantidade: 1,
      valor_unitario: 0.00,
      valor_total: 0.00,
      loadingPrice: false
    };

    setPedido({ ...pedido, itens: [...pedido.itens, newItem] });
  };

  // Remove linha
  const removeItem = (index) => {
    const novosItens = [...pedido.itens];
    novosItens.splice(index, 1);
    setPedido({ ...pedido, itens: novosItens });
  };

  // Atualiza Qtd ou Preço e recalcula
  const updateItemValue = (index, field, value) => {
    const novosItens = [...pedido.itens];
    novosItens[index][field] = value;

    const qtd = parseFloat(novosItens[index].quantidade) || 0;
    const val = parseFloat(novosItens[index].valor_unitario) || 0;
    novosItens[index].valor_total = (qtd * val).toFixed(2);

    setPedido({ ...pedido, itens: novosItens });
  };

  // Quando escolhe um produto no Autocomplete
  const handleProductSelect = async (index, prodWinthor) => {
    const novosItens = [...pedido.itens];
    novosItens[index].produto = prodWinthor;
    novosItens[index].loadingPrice = true;
    setPedido({ ...pedido, itens: novosItens });

    try {
      // Chama a nova API para buscar o preço base na região do cliente!
      const { data } = await api.post('/produtos/preco', {
        cliente_id: pedido.cliente.id,
        produto_id: prodWinthor.id
      });

      if (data.encontrado) {
        novosItens[index].valor_unitario = parseFloat(data.preco).toFixed(2);
        
        // Já calcula o total com a qtd atual (que por padrão é 1)
        const qtd = parseFloat(novosItens[index].quantidade) || 0;
        novosItens[index].valor_total = (qtd * parseFloat(data.preco)).toFixed(2);
      }
    } catch (error) {
      console.error("Erro ao buscar preço:", error);
      alert("Não foi possível buscar o preço padrão. Digite manualmente.");
    } finally {
      novosItens[index].loadingPrice = false;
      setPedido({ ...pedido, itens: [...novosItens] });
    }
  };

  // Enviar Pedido para o Backend
  const handleSaveAndSend = async () => {
    if (!pedido.cliente) return alert("Selecione o Cliente.");
    if (pedido.itens.length === 0) return alert("Adicione pelo menos um produto.");
    
    // Valida se todos os itens têm produto selecionado
    const hasEmptyProduct = pedido.itens.some(i => !i.produto);
    if (hasEmptyProduct) return alert("Você tem linhas em branco. Selecione um produto ou remova a linha.");

    setSaving(true);
    try {
      // Monta o Payload no formato que sua rota /pedidos/manual espera
      const payload = {
        cliente_id: pedido.cliente.id,
        options: pedido.options,
        itens: pedido.itens.map(i => ({
          id_produto: i.produto.id,
          quantidade: parseFloat(i.quantidade),
          valor: parseFloat(i.valor_unitario)
        }))
      };

      const { data } = await api.post('/pedidos/manual', payload);
      
      alert("Pedido Manual gerado e enviado para validação com sucesso!");
      navigate(`/pedido/${data.job_id}`); // Redireciona para a tela de revisão dele (para confirmar o envio)
      // Ou se quiser ir direto pro dashboard: navigate('/')
      
    } catch (error) {
      alert("Erro ao enviar pedido manual: " + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  // Calcula Totais Finais
  const totalPedido = pedido.itens.reduce((acc, item) => acc + (parseFloat(item.valor_total) || 0), 0);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <button onClick={() => navigate('/')} className="flex items-center text-gray-600 hover:text-blue-600 font-medium">
          <ArrowLeft className="w-5 h-5 mr-1" /> Voltar
        </button>
        <h1 className="text-2xl font-bold text-gray-800 flex items-center">
          <ShoppingCart className="w-6 h-6 mr-2 text-blue-600" /> Digitação de Pedido
        </h1>
        <button
          onClick={handleSaveAndSend}
          disabled={saving || !pedido.cliente || pedido.itens.length === 0}
          className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-md shadow flex items-center font-bold disabled:bg-green-300"
        >
          {saving ? 'Processando...' : <><Save className="w-5 h-5 mr-2" /> Gerar Pedido</>}
        </button>
      </div>

      {/* 1. Seleção do Cliente */}
      <div className="bg-white p-6 rounded-lg shadow mb-6 border-t-4 border-blue-600">
        <h3 className="text-lg font-bold text-gray-800 mb-4">1. Informações do Cliente</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Buscar Cliente (CNPJ, Razão ou ID)</label>
            <ClientSearch onSelect={handleClientSelect} />
          </div>
          <div className="flex flex-col justify-end pb-2">
            <label className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded border">
              <input 
                type="checkbox" 
                checked={pedido.options.is_bonificacao}
                onChange={(e) => setPedido({...pedido, options: {...pedido.options, is_bonificacao: e.target.checked}})}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-sm font-medium text-gray-700">É Bonificação?</span>
            </label>
          </div>
        </div>

        {/* Resumo do Cliente Selecionado */}
        {pedido.cliente && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded text-sm text-blue-800 flex justify-between">
            <span><strong>Selecionado:</strong> {pedido.cliente.id} - {pedido.cliente.razao_social}</span>
            <span><strong>CNPJ/CPF:</strong> {pedido.cliente.cnpj_cpf}</span>
          </div>
        )}
      </div>

      {/* 2. Tabela de Produtos */}
      <div className={`bg-white shadow rounded-lg overflow-hidden transition-opacity ${!pedido.cliente ? 'opacity-50 pointer-events-none' : ''}`}>
        <div className="p-4 bg-gray-50 border-b flex justify-between items-center">
          <h3 className="text-lg font-bold text-gray-800">2. Itens do Pedido</h3>
          <span className="font-bold text-xl text-green-700">Total: R$ {totalPedido.toFixed(2)}</span>
        </div>

        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase w-1/2">Produto</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Quantidade</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Vlr. Unitário</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Linha</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Ações</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {pedido.itens.length === 0 && (
              <tr>
                <td colSpan="5" className="px-4 py-8 text-center text-gray-500">
                  Nenhum produto adicionado. Clique abaixo para incluir.
                </td>
              </tr>
            )}
            
            {pedido.itens.map((item, idx) => (
              <tr key={item.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  {/* Se já escolheu o produto, não deixa pesquisar de novo na mesma linha (obriga a apagar) */}
                  {item.produto ? (
                    <div className="font-medium text-gray-900 text-sm">
                      {item.produto.id} - {item.produto.nome}
                      <span className="block text-xs text-gray-500">EAN: {item.produto.ean || 'N/A'}</span>
                    </div>
                  ) : (
                    <ProductSearch onSelect={(prod) => handleProductSelect(idx, prod)} />
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <input 
                    type="number" 
                    min="1"
                    className="w-20 border border-gray-300 rounded p-1 text-right focus:ring-blue-500 text-sm"
                    value={item.quantidade}
                    onChange={(e) => updateItemValue(idx, 'quantidade', e.target.value)}
                    disabled={!item.produto}
                  />
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="relative">
                    <input 
                      type="number" 
                      step="0.01"
                      className="w-24 border border-gray-300 rounded p-1 text-right focus:ring-blue-500 text-sm"
                      value={item.valor_unitario}
                      onChange={(e) => updateItemValue(idx, 'valor_unitario', e.target.value)}
                      disabled={!item.produto || item.loadingPrice}
                    />
                    {item.loadingPrice && <span className="absolute -left-6 top-2 text-xs text-blue-500 animate-pulse">Buscando...</span>}
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-bold text-gray-700">
                  R$ {item.valor_total}
                </td>
                <td className="px-4 py-3 text-center">
                  <button 
                    onClick={() => removeItem(idx)}
                    className="text-red-400 hover:text-red-600 transition-colors"
                    title="Remover Linha"
                  >
                    <Trash2 className="w-5 h-5 mx-auto" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Botão Adicionar Produto */}
        <div className="bg-gray-50 border-t border-gray-200 p-4">
          <button 
            onClick={addNewItem}
            className="flex items-center text-sm text-blue-600 font-bold hover:text-blue-800 transition-colors"
          >
            <Plus className="w-4 h-4 mr-1" /> Adicionar Produto
          </button>
        </div>
      </div>
    </div>
  );
}
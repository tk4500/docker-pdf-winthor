import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import ClientSearch from '../components/ClientSearch';
import ProductSearch from '../components/ProductSearch';
import { Save, ArrowLeft, Plus, Trash2, ShoppingCart } from 'lucide-react';

export default function PedidoManual() {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  
  const [pedido, setPedido] = useState({
    numero_pedido: "",
    cliente: null,
    itens: [],
    options: {
      auto_process: true,
      is_bonificacao: false
    }
  });

  const handleClientSelect = (cliWinthor) => {
    setPedido({ ...pedido, cliente: cliWinthor });
    // Se não tiver itens, cria o primeiro e foca nele automaticamente
    if (pedido.itens.length === 0) {
      setTimeout(addNewItem, 100);
    }
  };

  const addNewItem = () => {
    if (!pedido.cliente) {
      alert("Selecione um cliente primeiro para podermos buscar os preços corretos da região.");
      return;
    }

    const newItem = {
      id: Date.now(),
      produto: null,
      quantidade: 1,
      valor_unitario: 0.00,
      valor_total: 0.00,
      loadingPrice: false
    };

    setPedido((prev) => ({ ...prev, itens: [...prev.itens, newItem] }));
  };

  const removeItem = (index) => {
    const novosItens = [...pedido.itens];
    novosItens.splice(index, 1);
    setPedido({ ...pedido, itens: novosItens });
  };

  const updateItemValue = (index, field, value) => {
    const novosItens = [...pedido.itens];
    novosItens[index][field] = value;

    const qtd = parseFloat(novosItens[index].quantidade) || 0;
    const val = parseFloat(novosItens[index].valor_unitario) || 0;
    novosItens[index].valor_total = (qtd * val).toFixed(2);

    setPedido({ ...pedido, itens: novosItens });
  };

  const handleProductSelect = async (index, prodWinthor) => {
    const novosItens = [...pedido.itens];
    novosItens[index].produto = prodWinthor;
    novosItens[index].loadingPrice = true;
    setPedido({ ...pedido, itens: novosItens });

    try {
      const { data } = await api.post('/produtos/preco', {
        cliente_id: pedido.cliente.id,
        produto_id: prodWinthor.id
      });

      if (data.encontrado) {
        novosItens[index].valor_unitario = parseFloat(data.preco).toFixed(2);
        const qtd = parseFloat(novosItens[index].quantidade) || 0;
        novosItens[index].valor_total = (qtd * parseFloat(data.preco)).toFixed(2);
      }
    } catch (error) {
      console.error("Erro ao buscar preço:", error);
    } finally {
      novosItens[index].loadingPrice = false;
      setPedido({ ...pedido, itens: [...novosItens] });
    }
  };

  // --- LOGICA DE DIGITAÇÃO RÁPIDA (ENTER) ---
  const handleQtdKeyDown = (e, idx) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      // Pula para o campo Preço da mesma linha
      document.getElementById(`val-input-${idx}`)?.focus();
      document.getElementById(`val-input-${idx}`)?.select();
    }
  };

  const handleValKeyDown = (e, idx) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      // Cria a nova linha (que receberá foco automático na pesquisa)
      addNewItem();
    }
  };

  const handleSaveAndSend = async () => {
    if (!pedido.cliente) return alert("Selecione o Cliente.");
    if (pedido.itens.length === 0) return alert("Adicione pelo menos um produto.");
    
    // Remove as linhas em branco automaticamente antes de enviar (melhor UX)
    const itensValidos = pedido.itens.filter(i => i.produto);
    if (itensValidos.length === 0) return alert("Nenhum produto válido na tabela.");

    setSaving(true);
    try {
      const payload = {
        numero_pedido: pedido.numero_pedido,
        cliente_id: pedido.cliente.id,
        options: pedido.options,
        itens: itensValidos.map(i => ({
          id_produto: i.produto.id,
          quantidade: parseFloat(i.quantidade),
          valor: parseFloat(i.valor_unitario)
        }))
      };

      const { data } = await api.post('/pedidos/manual', payload);
      alert("Pedido Manual gerado com sucesso!");
      navigate(`/pedido/${data.job_id}`);
    } catch (error) {
      alert("Erro ao enviar pedido manual: " + (error.response?.data?.detail || error.message));
    } finally {
      setSaving(false);
    }
  };

  const totalPedido = pedido.itens.reduce((acc, item) => acc + (parseFloat(item.valor_total) || 0), 0);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* CABEÇALHO (Igual ao anterior) */}
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

      <div className="bg-white p-6 rounded-lg shadow mb-6 border-t-4 border-blue-600">
        <h3 className="text-lg font-bold text-gray-800 mb-4">1. Informações do Pedido</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="md:col-span-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">Número do Pedido</label>
            <input 
              type="text"
              placeholder="Opcional"
              value={pedido.numero_pedido}
              onChange={(e) => setPedido({...pedido, numero_pedido: e.target.value})}
              className="w-full border border-gray-300 rounded p-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Buscar Cliente (CNPJ, Razão ou ID)</label>
            <ClientSearch onSelect={handleClientSelect} />
          </div>
          <div className="flex flex-col justify-end pb-2">
            <label className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded border border-gray-200">
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
        {pedido.cliente && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-100 rounded text-sm text-blue-800 flex justify-between">
            <span><strong>Selecionado:</strong> {pedido.cliente.id} - {pedido.cliente.razao_social}</span>
            <span><strong>CNPJ/CPF:</strong> {pedido.cliente.cnpj_cpf}</span>
          </div>
        )}
      </div>

      <div className={`bg-white shadow rounded-lg transition-opacity ${!pedido.cliente ? 'opacity-50 pointer-events-none' : ''}`}>
        <div className="p-4 bg-gray-50 border-b flex justify-between items-center rounded-t-lg">
          <h3 className="text-lg font-bold text-gray-800">2. Itens do Pedido</h3>
          <span className="font-bold text-xl text-green-700">Total: R$ {totalPedido.toFixed(2)}</span>
        </div>

        <div className="overflow-visible w-full pb-20"> 
          <table className="min-w-full divide-y divide-gray-200 border-b">
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
                    Nenhum produto. Selecione um cliente para começar!
                  </td>
                </tr>
              )}
              
              {pedido.itens.map((item, idx) => (
                <tr key={item.id} className="hover:bg-gray-50 relative">
                  <td className="px-4 py-3 overflow-visible">
                    {item.produto ? (
                      <div className="font-medium text-gray-900 text-sm">
                        {item.produto.id} - {item.produto.nome}
                        <span className="block text-xs text-gray-500">EAN: {item.produto.ean || 'N/A'}</span>
                      </div>
                    ) : (
                      // AQUI PASSAMOS O rowIndex e autoFocus = true
                      <ProductSearch 
                        autoFocus={true} 
                        rowIndex={idx} 
                        onSelect={(prod) => handleProductSelect(idx, prod)} 
                      />
                    )}
                  </td>
                  <td className="px-4 py-3 text-right align-top">
                    {/* ID e handleQtdKeyDown adicionados */}
                    <input 
                      id={`qtd-input-${idx}`}
                      type="number" 
                      min="1"
                      className="w-20 border border-gray-300 rounded p-1 text-right focus:ring-blue-500 focus:border-blue-500 text-sm outline-none"
                      value={item.quantidade}
                      onChange={(e) => updateItemValue(idx, 'quantidade', e.target.value)}
                      onKeyDown={(e) => handleQtdKeyDown(e, idx)}
                      disabled={!item.produto}
                    />
                  </td>
                  <td className="px-4 py-3 text-right align-top">
                    <div className="relative">
                      {/* ID e handleValKeyDown adicionados */}
                      <input 
                        id={`val-input-${idx}`}
                        type="number" 
                        step="0.01"
                        className="w-24 border border-gray-300 rounded p-1 text-right focus:ring-blue-500 focus:border-blue-500 text-sm outline-none"
                        value={item.valor_unitario}
                        onChange={(e) => updateItemValue(idx, 'valor_unitario', e.target.value)}
                        onKeyDown={(e) => handleValKeyDown(e, idx)}
                        disabled={!item.produto} // Removi o disabled={item.loadingPrice} pra não tirar o foco do usuário
                      />
                      {item.loadingPrice && <span className="absolute -left-6 top-2 text-xs text-blue-500 animate-pulse">Buscando...</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-bold text-gray-700 align-top pt-4">
                    R$ {item.valor_total}
                  </td>
                  <td className="px-4 py-3 text-center align-top pt-4">
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
        </div>

        <div className="bg-gray-50 border-t border-gray-200 p-4 rounded-b-lg">
          <button 
            onClick={addNewItem}
            className="flex items-center text-sm text-blue-600 font-bold hover:text-blue-800 transition-colors"
          >
            <Plus className="w-4 h-4 mr-1" /> Adicionar Produto (Manual)
          </button>
        </div>
      </div>
    </div>
  );
}
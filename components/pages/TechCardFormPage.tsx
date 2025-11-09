
import React, { useState, useRef } from 'react';
import { TechCardFormData, TechCardData } from '../../types';
import { generateTechCardContent } from '../../services/geminiService';
import { generateDocument } from '../../services/documentGenerator';
import Card from '../shared/Card';
import Input from '../shared/Input';
import Button from '../shared/Button';
import Spinner from '../shared/Spinner';
import Modal from '../shared/Modal';
import TechCardTemplate from '../document/TechCardTemplate';

const initialFormData: TechCardFormData = {
  customer: 'ПАО "Газпром"',
  facility: 'МГ "Сила Сибири"',
  weldConnectionNumber: 'SS-01-001',
  controlObject: 'Кольцевой сварной шов',
  normativeDocument: 'СТО Газпром 2-2.4-083-2006',
  weldType: 'Стыковое',
  thickness: '12.5',
  diameter: '1420',
  controlMethod: 'Радиографический',
  qualityLevel: 'B (по ISO 5817)',
  sensitivity: 'Класс 2 по ГОСТ 7512',
  equipment: ['Источник излучения: РПД-250', 'Пленка: Agfa D7', 'Проявочная машина: "Омега"'],
};

const TechCardFormPage: React.FC = () => {
  const [formData, setFormData] = useState<TechCardFormData>(initialFormData);
  const [generatedData, setGeneratedData] = useState<Partial<TechCardData> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  const documentRef = useRef<HTMLDivElement>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };
  
  const handleEquipmentChange = (index: number, value: string) => {
    const newEquipment = [...formData.equipment];
    newEquipment[index] = value;
    setFormData(prev => ({ ...prev, equipment: newEquipment }));
  };

  const addEquipment = () => {
    setFormData(prev => ({ ...prev, equipment: [...prev.equipment, ''] }));
  };

  const removeEquipment = (index: number) => {
    const newEquipment = formData.equipment.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, equipment: newEquipment }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setGeneratedData(null);

    try {
      const result = await generateTechCardContent(formData);
      setGeneratedData(result);
      setIsModalOpen(true);
    } catch (err: any) {
      setError(err.message || 'Произошла неизвестная ошибка.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async (format: 'pdf' | 'docx') => {
    if (!documentRef.current || !generatedData) return;
    setIsDownloading(true);
    try {
      await generateDocument(
          documentRef.current, 
          `TechCard_${formData.weldConnectionNumber}`, 
          format
      );
    } catch (downloadError) {
      console.error(`Error downloading ${format}:`, downloadError);
      setError(`Не удалось скачать ${format} файл.`);
    } finally {
      setIsDownloading(false);
    }
  };

  const fullCardData: TechCardData | null = generatedData ? { ...formData, ...generatedData } as TechCardData : null;

  return (
    <>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Создание технологической карты</h1>
        <p className="text-slate-600 mb-8">Заполните поля ниже, чтобы сгенерировать техкарту. Поля, отмеченные *, обязательны.</p>

        <form onSubmit={handleSubmit}>
          <Card>
            <h2 className="text-xl font-bold text-slate-800 border-b-2 border-primary-200 pb-2 mb-6">Информация об объекте</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input label="Заказчик" name="customer" value={formData.customer} onChange={handleInputChange} required />
              <Input label="Объект" name="facility" value={formData.facility} onChange={handleInputChange} required />
              <Input label="Номер сварного соединения" name="weldConnectionNumber" value={formData.weldConnectionNumber} onChange={handleInputChange} required />
              <Input label="Объект контроля" name="controlObject" value={formData.controlObject} onChange={handleInputChange} required />
            </div>
          </Card>

          <Card className="mt-6">
            <h2 className="text-xl font-bold text-slate-800 border-b-2 border-primary-200 pb-2 mb-6">Параметры контроля</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input label="Нормативный документ" name="normativeDocument" value={formData.normativeDocument} onChange={handleInputChange} required />
              <Input label="Тип сварного соединения" name="weldType" value={formData.weldType} onChange={handleInputChange} required />
              <Input label="Толщина, мм" name="thickness" type="number" value={formData.thickness} onChange={handleInputChange} required />
              <Input label="Диаметр, мм" name="diameter" type="number" value={formData.diameter} onChange={handleInputChange} required />
              <div>
                <label htmlFor="controlMethod" className="block text-sm font-medium text-gray-700 mb-1">Метод контроля</label>
                <select id="controlMethod" name="controlMethod" value={formData.controlMethod} onChange={handleInputChange} className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-md">
                  <option>Радиографический</option>
                  <option>Ультразвуковой</option>
                  <option>Визуальный и измерительный</option>
                  <option>Капиллярный</option>
                  <option>Магнитопорошковый</option>
                </select>
              </div>
              <Input label="Уровень качества" name="qualityLevel" value={formData.qualityLevel} onChange={handleInputChange} required />
              <Input label="Чувствительность" name="sensitivity" value={formData.sensitivity} onChange={handleInputChange} required />
            </div>
          </Card>

           <Card className="mt-6">
            <h2 className="text-xl font-bold text-slate-800 border-b-2 border-primary-200 pb-2 mb-6">Оборудование</h2>
             <div className="space-y-4">
              {formData.equipment.map((item, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input 
                    label={`Оборудование ${index + 1}`} 
                    value={item}
                    onChange={(e) => handleEquipmentChange(index, e.target.value)}
                    className="flex-grow"
                  />
                  <Button type="button" variant="danger" size="sm" onClick={() => removeEquipment(index)} className="mt-7">
                    -
                  </Button>
                </div>
              ))}
              </div>
              <Button type="button" variant="secondary" onClick={addEquipment} className="mt-4">Добавить оборудование</Button>
          </Card>

          <div className="mt-8 flex justify-end">
            <Button type="submit" size="lg" disabled={isLoading}>
              {isLoading ? <><Spinner className="mr-2" /> Генерация...</> : 'Сгенерировать техкарту'}
            </Button>
          </div>
        </form>

        {error && <p className="mt-4 text-center text-red-600">{error}</p>}
      </div>

      {isModalOpen && fullCardData && (
        <Modal 
          title={`Предпросмотр техкарты: ${fullCardData.weldConnectionNumber}`}
          onClose={() => setIsModalOpen(false)}
          footer={
            <div className="flex justify-end gap-4">
               <Button variant="secondary" onClick={() => setIsModalOpen(false)} disabled={isDownloading}>Закрыть</Button>
               <Button onClick={() => handleDownload('docx')} disabled={isDownloading}>
                {isDownloading ? <Spinner className="mr-2" /> : 'Скачать DOCX'}
               </Button>
               <Button onClick={() => handleDownload('pdf')} disabled={isDownloading}>
                {isDownloading ? <Spinner className="mr-2" /> : 'Скачать PDF'}
               </Button>
            </div>
          }
        >
          {/* This is a hidden element for download generation */}
           <div className="hidden">
              <TechCardTemplate ref={documentRef} data={fullCardData} />
           </div>
           {/* This is the visible preview */}
           <div className="p-8 bg-gray-100">
             <div className="bg-white shadow-lg p-12 mx-auto max-w-4xl">
               <TechCardTemplate data={fullCardData} />
             </div>
           </div>
        </Modal>
      )}
    </>
  );
};

export default TechCardFormPage;

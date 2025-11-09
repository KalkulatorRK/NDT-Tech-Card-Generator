
import React from 'react';
import Card from '../shared/Card';
import Button from '../shared/Button';

const TariffCard: React.FC<{ count: number; price: number; popular?: boolean }> = ({ count, price, popular }) => (
  <div className={`border rounded-lg p-6 text-center relative ${popular ? 'border-primary-500' : 'border-slate-300'}`}>
    {popular && <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary-500 text-white text-xs font-semibold px-3 py-1 rounded-full">Популярный</div>}
    <p className="text-2xl font-bold text-slate-900">{count} разработок</p>
    <p className="mt-4 text-4xl font-extrabold text-slate-900">{price}₽</p>
    <Button className="mt-6 w-full">Выбрать</Button>
  </div>
);


const DashboardPage: React.FC = () => {
  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Личный кабинет</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
            <h2 className="text-xl font-bold text-slate-800 mb-4">Ваши техкарты</h2>
            <Card>
                <div className="divide-y divide-slate-200">
                    <div className="p-4 flex justify-between items-center">
                        <div>
                            <p className="font-semibold text-primary-700">ТК № 02/11-РГК</p>
                            <p className="text-sm text-slate-500">Создано: 21.01.2024</p>
                        </div>
                        <div className="space-x-2">
                            <Button size="sm" variant="secondary">Просмотр</Button>
                            <Button size="sm">Скачать</Button>
                        </div>
                    </div>
                     <div className="p-4 flex justify-between items-center">
                        <div>
                            <p className="font-semibold text-primary-700">ТК № 03/11-ВИК</p>
                            <p className="text-sm text-slate-500">Создано: 15.01.2024</p>
                        </div>
                        <div className="space-x-2">
                            <Button size="sm" variant="secondary">Просмотр</Button>
                            <Button size="sm">Скачать</Button>
                        </div>
                    </div>
                </div>
            </Card>
        </div>
        <div>
            <h2 className="text-xl font-bold text-slate-800 mb-4">Статус и оплата</h2>
            <Card>
                <p className="text-lg">Вам доступно:</p>
                <p className="text-5xl font-extrabold text-primary my-2">3</p>
                <p className="text-lg mb-6">разработки техкарт.</p>
                <h3 className="font-semibold text-slate-800 mb-4">Пополнить баланс:</h3>
                <div className="space-y-4">
                  <TariffCard count={5} price={800} popular />
                  <TariffCard count={1} price={300} />
                  <TariffCard count={10} price={1500} />
                </div>
            </Card>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;

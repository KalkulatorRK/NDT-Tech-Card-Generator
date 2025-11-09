
import React from 'react';
import { Page } from '../../types';
import Button from '../shared/Button';
import Card from '../shared/Card';

interface HomePageProps {
  navigate: (page: Page) => void;
}

const FeatureCard: React.FC<{ title: string; description: string; icon: React.ReactNode }> = ({ title, description, icon }) => (
    <Card>
        <div className="flex items-center justify-center h-12 w-12 rounded-md bg-primary-500 text-white mb-4">
            {icon}
        </div>
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        <p className="mt-2 text-base text-slate-600">{description}</p>
    </Card>
);

const FileIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
);

const CheckSquareIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg>
);

const UserIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
);


const HomePage: React.FC<HomePageProps> = ({ navigate }) => {
  return (
    <div className="text-center">
      <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight">
        Автоматизируйте создание <span className="text-primary">техкарт</span> неразрушающего контроля
      </h1>
      <p className="mt-6 max-w-2xl mx-auto text-lg text-slate-600">
        Создавайте профессиональные технологические карты и проводите оценку качества сварных швов быстро и точно, в соответствии с действующими стандартами.
      </p>
      <div className="mt-8 flex justify-center gap-4">
        <Button onClick={() => navigate(Page.CreateTechCard)} size="lg">
          Создать техкарту
        </Button>
        <Button onClick={() => navigate(Page.QualityAssessment)} variant="secondary" size="lg">
          Оценить качество
        </Button>
      </div>

      <div className="mt-20">
        <h2 className="text-3xl font-bold tracking-tight text-slate-900">Ключевые возможности</h2>
        <div className="mt-10 grid gap-8 md:grid-cols-3">
           <FeatureCard
             title="Генерация техкарт"
             description="Введите параметры вашего объекта и получите готовую технологическую карту в форматах DOCX и PDF."
             icon={<FileIcon />}
           />
           <FeatureCard
             title="Оценка качества"
             description="Проверьте соответствие обнаруженных дефектов требованиям нормативных документов с помощью нашего инструмента оценки."
             icon={<CheckSquareIcon />}
            />
           <FeatureCard
             title="Личный кабинет"
             description="Все ваши документы хранятся в одном месте. Управляйте, скачивайте и редактируйте их в любое время."
             icon={<UserIcon />}
           />
        </div>
      </div>
    </div>
  );
};

export default HomePage;

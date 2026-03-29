import { useNavigate } from 'react-router-dom';
import { Upload, FileText, Users, ArrowRight, ShieldCheck } from 'lucide-react';
import './Home.css';

export const Home = () => {
    const navigate = useNavigate();

    return (
        <div className="home-container">
            {/* Hero Section */}
            <section className="hero-section">
                <h1 className="hero-title">Welcome to DocuServe</h1>
                <p className="hero-description">
                    Experience the future of document management with <strong>DocuServe</strong>.
                    A unified workspace that empowers teams to upload, secure, and collaborate on files in real-time.
                    From effortless version control to instant search, we transform your repository into a dynamic knowledge engine.
                </p>
                <div className="hero-actions">
                    <button
                        className="cta-button cta-primary"
                        onClick={() => navigate('/documents')}
                    >
                        Go to Workspace <ArrowRight size={20} style={{ marginLeft: '0.5rem' }} />
                    </button>
                    <button
                        className="cta-button cta-secondary"
                        onClick={() => navigate('/upload')}
                    >
                        <Upload size={20} style={{ marginRight: '0.5rem' }} /> Upload File
                    </button>
                </div>
            </section>

            {/* Features Grid */}
            <section className="features-grid">
                <div className="feature-card">
                    <div className="feature-icon-wrapper icon-blue">
                        <FileText size={28} />
                    </div>
                    <h3 className="feature-title">Universal Storage</h3>
                    <p className="feature-text">
                        Securely store any file type, from documents and spreadsheets to images and code.
                        Preview them instantly without leaving the platform.
                    </p>
                </div>

                <div className="feature-card">
                    <div className="feature-icon-wrapper icon-purple">
                        <Users size={28} />
                    </div>
                    <h3 className="feature-title">Real-time Collaboration</h3>
                    <p className="feature-text">
                        Work together with your team. active presence, live editing, and detailed
                        version history ensure everyone stays on the same page.
                    </p>
                </div>

                <div className="feature-card">
                    <div className="feature-icon-wrapper icon-green">
                        <ShieldCheck size={28} />
                    </div>
                    <h3 className="feature-title">Secure & Organized</h3>
                    <p className="feature-text">
                        Keep your data safe with robust permissions. Organize effortlessly
                        using smart tags, metadata filters, and powerful full-text search.
                    </p>
                </div>
            </section>
        </div>
    );
};

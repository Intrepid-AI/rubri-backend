import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardHeader, CardContent, Button } from '../ui';
import '../../styles/markdown-enhanced.css';
import { 
  Download, 
  Share2, 
  Copy, 
  CheckCircle, 
  Clock, 
  Users, 
  Target,
  FileText,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Search,
  List,
  BarChart3,
  Zap,
  Sparkles,
  TrendingUp
} from 'lucide-react';
import type { QuestionGenerationResponse } from '../../types/api';

interface ReportViewerProps {
  result: QuestionGenerationResponse;
  onExport?: (format: 'pdf' | 'link') => void;
}

interface SectionData {
  id: string;
  title: string;
  content: string;
  isVisible: boolean;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({
  result,
  onExport
}) => {
  const [copied, setCopied] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [showTableOfContents, setShowTableOfContents] = useState(false);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const handleCopyReport = async () => {
    if (result.formatted_report) {
      await navigator.clipboard.writeText(result.formatted_report);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDuration = (minutes?: number) => {
    if (!minutes) return 'N/A';
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const toggleSection = (sectionId: string) => {
    const newCollapsed = new Set(collapsedSections);
    if (newCollapsed.has(sectionId)) {
      newCollapsed.delete(sectionId);
    } else {
      newCollapsed.add(sectionId);
    }
    setCollapsedSections(newCollapsed);
  };

  const generateTableOfContents = () => {
    if (!result.formatted_report) return [];
    const lines = result.formatted_report.split('\n');
    const toc: Array<{id: string, title: string, level: number}> = [];
    
    lines.forEach((line, index) => {
      const match = line.match(/^(#{1,6})\s+(.+)$/);
      if (match) {
        const level = match[1].length;
        const title = match[2];
        const id = `section-${index}`;
        toc.push({ id, title, level });
      }
    });
    
    return toc;
  };

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
      setActiveSection(sectionId);
    }
  };

  const filteredContent = result.formatted_report && searchTerm
    ? result.formatted_report.split('\n').filter(line =>
        line.toLowerCase().includes(searchTerm.toLowerCase())
      ).join('\n')
    : result.formatted_report;

  const tableOfContents = generateTableOfContents();

  const getSkillDistribution = () => {
    if (!result.formatted_report) return [];
    
    // Extract skills from the report content
    const skillMatches = result.formatted_report.match(/\*\*([^\*]+)\*\*\s*\(([^)]+)\)/g) || [];
    const skills: {[key: string]: number} = {};
    
    skillMatches.forEach(match => {
      const skillMatch = match.match(/\*\*([^\*]+)\*\*\s*\(([^)]+)\)/);
      if (skillMatch) {
        const category = skillMatch[2];
        skills[category] = (skills[category] || 0) + 1;
      }
    });
    
    return Object.entries(skills).map(([category, count]) => ({ category, count }));
  };

  const skillDistribution = getSkillDistribution();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header with Metrics */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-foreground mb-2">
                Interview Questions for {result.position_title}
              </h1>
              {result.candidate_name && (
                <p className="text-foreground-muted">
                  Candidate: <span className="font-medium">{result.candidate_name}</span>
                </p>
              )}
              <div className="flex items-center gap-4 text-sm text-foreground-subtle mt-1">
                <div className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  Generated in {result.processing_time.toFixed(1)}s
                </div>
                <div className="flex items-center gap-1">
                  <FileText className="h-4 w-4" />
                  Input: {result.input_scenario}
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyReport}
                disabled={!result.formatted_report}
              >
                {copied ? (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy
                  </>
                )}
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => onExport?.('pdf')}
              >
                <Download className="h-4 w-4 mr-2" />
                Export PDF
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => onExport?.('link')}
              >
                <Share2 className="h-4 w-4 mr-2" />
                Share Link
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          {/* Enhanced Search and Navigation */}
          <div className="flex flex-col sm:flex-row gap-4 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search report content..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <Button
              variant="outline"
              onClick={() => setShowTableOfContents(!showTableOfContents)}
              className="flex items-center gap-2"
            >
              <List className="h-4 w-4" />
              {showTableOfContents ? 'Hide' : 'Show'} Contents
            </Button>
          </div>
          
          {/* Table of Contents */}
          {showTableOfContents && tableOfContents.length > 0 && (
            <Card className="mb-6 bg-gray-50">
              <CardHeader>
                <h3 className="text-lg font-semibold text-gray-900">Table of Contents</h3>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {tableOfContents.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => scrollToSection(item.id)}
                      className={`block w-full text-left py-2 px-3 rounded hover:bg-gray-100 transition-colors ${
                        activeSection === item.id ? 'bg-blue-100 text-blue-700' : 'text-gray-700'
                      }`}
                      style={{ paddingLeft: `${item.level * 16}px` }}
                    >
                      {item.title}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
          
          {/* Enhanced Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="text-center group hover:transform hover:scale-105 transition-all duration-200">
              <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-blue-500/20 to-blue-600/20 rounded-lg mx-auto mb-2 group-hover:from-blue-500/30 group-hover:to-blue-600/30">
                <Target className="h-6 w-6 text-blue-500" />
              </div>
              <p className="text-2xl font-bold text-foreground group-hover:text-blue-600">
                {result.skills_identified || 0}
              </p>
              <p className="text-sm text-foreground-muted">Skills Identified</p>
            </div>
            
            <div className="text-center group hover:transform hover:scale-105 transition-all duration-200">
              <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-green-500/20 to-green-600/20 rounded-lg mx-auto mb-2 group-hover:from-green-500/30 group-hover:to-green-600/30">
                <FileText className="h-6 w-6 text-green-500" />
              </div>
              <p className="text-2xl font-bold text-foreground group-hover:text-green-600">
                {result.questions_generated || 0}
              </p>
              <p className="text-sm text-foreground-muted">Questions Generated</p>
            </div>
            
            <div className="text-center group hover:transform hover:scale-105 transition-all duration-200">
              <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-purple-500/20 to-purple-600/20 rounded-lg mx-auto mb-2 group-hover:from-purple-500/30 group-hover:to-purple-600/30">
                <Clock className="h-6 w-6 text-purple-500" />
              </div>
              <p className="text-2xl font-bold text-foreground group-hover:text-purple-600">
                {formatDuration(result.interview_duration_minutes || undefined)}
              </p>
              <p className="text-sm text-foreground-muted">Est. Duration</p>
            </div>
            
            <div className="text-center group hover:transform hover:scale-105 transition-all duration-200">
              <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-orange-500/20 to-orange-600/20 rounded-lg mx-auto mb-2 group-hover:from-orange-500/30 group-hover:to-orange-600/30">
                <Users className="h-6 w-6 text-orange-500" />
              </div>
              <p className="text-2xl font-bold text-foreground group-hover:text-orange-600">
                {result.sections_created || 0}
              </p>
              <p className="text-sm text-foreground-muted">Sections</p>
            </div>
          </div>
          
          {/* Skill Distribution Chart */}
          {skillDistribution.length > 0 && (
            <div className="mt-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                Skill Distribution
              </h4>
              <div className="space-y-3">
                {skillDistribution.map((skill, index) => (
                  <div key={skill.category} className="flex items-center gap-3">
                    <div className="w-24 text-sm text-gray-600 font-medium">
                      {skill.category}
                    </div>
                    <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div
                        className="h-2 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all duration-1000 ease-out"
                        style={{ 
                          width: `${(skill.count / Math.max(...skillDistribution.map(s => s.count))) * 100}%`,
                          transitionDelay: `${index * 100}ms`
                        }}
                      />
                    </div>
                    <div className="w-8 text-sm text-gray-500 font-medium">
                      {skill.count}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Key Insights */}
      {(result.key_strengths || result.potential_concerns || result.focus_areas) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {result.key_strengths && result.key_strengths.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-green-400">Key Strengths</h3>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.key_strengths.map((strength, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-400 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-foreground-muted">{strength}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          
          {result.potential_concerns && result.potential_concerns.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-orange-400">Areas to Explore</h3>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.potential_concerns.map((concern, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <ArrowRight className="h-4 w-4 text-orange-400 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-foreground-muted">{concern}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
          
          {result.focus_areas && result.focus_areas.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-lg font-semibold text-blue-400">Focus Areas</h3>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.focus_areas.map((area, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <Target className="h-4 w-4 text-blue-400 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-foreground-muted">{area}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Overall Recommendation */}
      {result.overall_recommendation && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-foreground">Overall Recommendation</h3>
          </CardHeader>
          <CardContent>
            <p className="text-foreground-muted leading-relaxed">
              {result.overall_recommendation}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Main Report */}
      {result.formatted_report && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-foreground">Interview Questions & Guidance</h3>
            <p className="text-sm text-foreground-muted">
              Complete interview plan with questions, expected responses, and evaluation criteria
            </p>
          </CardHeader>
          <CardContent>
            <div className="markdown-enhanced max-w-none" spellCheck={false}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // Professional Link Components with enhanced styling
                  a: ({ href, children }) => (
                    <a href={href} className="text-primary-600 hover:text-primary-800 no-underline hover:underline transition-all duration-200" target="_blank" rel="noopener noreferrer" spellCheck={false}>
                      {children}
                      <ExternalLink className="inline h-3 w-3 ml-1" />
                    </a>
                  ),
                  // Enhanced Table Components - Let CSS handle the styling
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-6">
                      <table className="min-w-full">
                        {children}
                      </table>
                    </div>
                  ),
                  // Keep other components minimal to let CSS handle styling
                }}
              >
                {result.formatted_report}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agent Performance (for debugging) */}
      {result.agent_performance && import.meta.env.DEV && (
        <Card>
          <CardHeader>
            <h3 className="text-lg font-semibold text-foreground">Agent Performance</h3>
            <p className="text-sm text-foreground-muted">Debug information</p>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-surface-100 p-3 rounded-md overflow-x-auto text-foreground-muted">
              {JSON.stringify(result.agent_performance, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
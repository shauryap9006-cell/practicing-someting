import React, { useState } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Volume2, VolumeX, Copy, Check, Radio, Play } from 'lucide-react';
import { toast } from 'sonner';

export function AnnouncementsPage() {
  const [triggerType, setTriggerType] = useState('platform_change');
  const [trainNo, setTrainNo] = useState('12034');
  const [platform, setPlatform] = useState(3);
  const [delayMin, setDelayMin] = useState(25);
  const [englishScript, setEnglishScript] = useState(
    'Attention please! Train number 12034, arriving at Kanpur Central, is running late by 25 minutes and will now arrive on Platform Number 3. Inconvenience caused is deeply regretted.'
  );
  const [hindiScript, setHindiScript] = useState(
    'कृपया ध्यान दीजिए! गाड़ी संख्या 12034, कानपुर सेंट्रल पर 25 मिनट की देरी से चल रही है, और अब प्लेटफार्म संख्या 3 पर आएगी। यात्रियों को हुई असुविधा के लिए हमें खेद है।'
  );
  const [isCopied, setIsCopied] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.generateAnnouncement({
        train_no: trainNo,
        platform,
        delay_min: delayMin,
        type: triggerType,
      });

      setEnglishScript((res as { english_script: string }).english_script);
      setHindiScript((res as { hindi_script: string }).hindi_script);
      toast.success('Bilingual Public Address announcement scripts generated.');
    } catch {
      toast.error('Failed to generate announcement.');
    }
  };

  const handleSpeak = (text: string, lang: string) => {
    if (!('speechSynthesis' in window)) {
      toast.error('Web Speech Synthesis not supported in this browser.');
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = 0.9;
    utterance.onstart = () => setIsPlaying(true);
    utterance.onend = () => setIsPlaying(false);
    utterance.onerror = () => setIsPlaying(false);

    window.speechSynthesis.speak(utterance);
    toast.info(`Playing ${lang.startsWith('hi') ? 'Hindi' : 'English'} PA audio announcement...`);
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    toast.success('Script copied to clipboard.');
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="Station Automated PA Announcements · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <Volume2 className="w-4 h-4 text-[#FFB224]" />
            <span>Automated Multilingual Station Announcement Engine</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Standardized 3-Language Indian Railways Public Address (PA) Script & TTS Generator
          </p>
        </div>
      </div>

      {/* Grid: Generator Form & Bilingual Scripts Output */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Input Form */}
        <div className="lg:col-span-5 bg-[#15171A] border border-[#26282C] p-5 space-y-4">
          <div className="font-bold text-sm text-[#E8E8E6] border-b border-[#26282C] pb-2">
            Announcement Trigger Parameters
          </div>

          <form onSubmit={handleGenerate} className="space-y-3">
            <div>
              <label className="text-[10px] text-[#9A9DA3] block mb-1">Trigger Event</label>
              <select
                value={triggerType}
                onChange={e => setTriggerType(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
              >
                <option value="platform_change">Platform Change Alert</option>
                <option value="delay">Late Running Update</option>
                <option value="arrival">Train Imminent Arrival</option>
                <option value="general">General Safety / Security Alert</option>
              </select>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Train No</label>
                <input
                  type="text"
                  value={trainNo}
                  onChange={e => setTrainNo(e.target.value)}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6] font-bold"
                />
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Platform</label>
                <input
                  type="number"
                  value={platform}
                  onChange={e => setPlatform(parseInt(e.target.value))}
                  className="w-full bg-[#0E0F11] border border-[#FFB224] p-2 text-[#FFB224] font-bold"
                />
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Delay (Min)</label>
                <input
                  type="number"
                  value={delayMin}
                  onChange={e => setDelayMin(parseInt(e.target.value))}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs flex items-center justify-center gap-2 transition-colors"
            >
              <Radio className="w-4 h-4" />
              <span>Generate Standard PA Scripts</span>
            </button>
          </form>
        </div>

        {/* Right: Bilingual Script Outputs */}
        <div className="lg:col-span-7 space-y-4">
          {/* Hindi Script Card */}
          <div className="bg-[#15171A] border border-[#26282C] p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-[#26282C] pb-2">
              <span className="font-bold text-sm text-[#FFB224]">हिन्दी उद्घोषणा (Hindi Script)</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleSpeak(hindiScript, 'hi-IN')}
                  className="px-2.5 py-1 bg-[#1B1D21] border border-[#26282C] hover:border-[#FFB224] text-[#E8E8E6] flex items-center gap-1.5"
                >
                  <Play className="w-3 h-3 fill-current text-[#3ECF8E]" />
                  <span>Play TTS</span>
                </button>
                <button
                  onClick={() => handleCopy(hindiScript)}
                  className="px-2.5 py-1 bg-[#1B1D21] border border-[#26282C] text-[#9A9DA3] hover:text-[#E8E8E6]"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>

            <p className="text-sm font-sans text-[#E8E8E6] leading-relaxed bg-[#0E0F11] p-4 border border-[#26282C]">
              {hindiScript}
            </p>
          </div>

          {/* English Script Card */}
          <div className="bg-[#15171A] border border-[#26282C] p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-[#26282C] pb-2">
              <span className="font-bold text-sm text-[#E8E8E6]">English Announcement (Script)</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleSpeak(englishScript, 'en-IN')}
                  className="px-2.5 py-1 bg-[#1B1D21] border border-[#26282C] hover:border-[#FFB224] text-[#E8E8E6] flex items-center gap-1.5"
                >
                  <Play className="w-3 h-3 fill-current text-[#3ECF8E]" />
                  <span>Play TTS</span>
                </button>
                <button
                  onClick={() => handleCopy(englishScript)}
                  className="px-2.5 py-1 bg-[#1B1D21] border border-[#26282C] text-[#9A9DA3] hover:text-[#E8E8E6]"
                >
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>

            <p className="text-xs font-sans text-[#E8E8E6] leading-relaxed bg-[#0E0F11] p-4 border border-[#26282C]">
              {englishScript}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Search, Check } from 'lucide-react'
import { Separator } from "@/components/ui/separator"
import { Card, CardContent } from "@/components/ui/card"

interface InsuranceCompanyModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete: (companies: string[] | null) => void
  initialSelectedCompanies: string[]
  onStartChat: (type: string, title?: string, initialMessage?: string) => void
}

const INSURANCE_COMPANIES_CATEGORIZED = {
  "생명보험": [
    "삼성생명", "한화생명", "교보생명", "신한생명", "미래에셋생명", "동양생명", "푸르덴셜생명", "메트라이프생명",
    "KB생명", "IBK연금보험", "농협생명", "우체국보험", "KDB생명", "오렌지라이프", "BNP파리바카디프생명", "DGB생명", "하나생명",
    "라이나생명", "AIA생명", "ABL생명"
  ],
  "손해보험": [
    "삼성화재", "현대해상", "DB손해보험", "KB손해보험", "메리츠화재", "한화손해보험", "롯데손해보험", "MG손해보험", "흥국화재", "캐롯손해보험"
  ],
  "제3보험": [] // 제3보험은 생명/손해보험사에서 취급하는 특정 상품군이므로, 여기에 별도 회사를 나열하기보다 위 카테고리 내에서 선택하는 것이 일반적입니다.
}

const INSURANCE_COMPANY_ICONS: { [key: string]: string } = {
  "삼성화재": "🔥", "현대해상": "🚗", "DB손해보험": "🏦", "KB손해보험": "🏛️", "메리츠화재": "⭐", 
  "한화손해보험": "🌸", "롯데손해보험": "🎯", "MG손해보험": "🚙", "흥국화재": "🏠", "캐롯손해보험": "🥕",
  "삼성생명": "💎", "한화생명": "🌺", "교보생명": "📚", "신한생명": "🏢", "미래에셋생명": "🚀", 
  "동양생명": "🌅", "푸르덴셜생명": "💼", "메트라이프생명": "🏙️", "라이나생명": "🦁", "AIA생명": "🌟",
  "KB생명": "🏦", "IBK연금보험": "🏛️", "농협생명": "🌾", "우체국보험": "📮", "KDB생명": "🏗️", 
  "ABL생명": "📊", "오렌지라이프": "🍊", "BNP파리바카디프생명": "🇫🇷", "DGB생명": "💰", "하나생명": "🌱"
}

export default function InsuranceCompanyModal({ isOpen, onClose, onComplete, initialSelectedCompanies, onStartChat }: InsuranceCompanyModalProps) {
  const [insuranceInput, setInsuranceInput] = useState("")
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>(initialSelectedCompanies || [])
  const [searchTerm, setSearchTerm] = useState("")

  useEffect(() => {
    setSelectedCompanies(initialSelectedCompanies || []);
  }, [initialSelectedCompanies]);

  const handleToggleCompany = (company: string) => {
    setSelectedCompanies((prev) =>
      prev.includes(company) ? prev.filter((c) => c !== company) : [...prev, company]
    )
  }

  const handleComplete = () => {
    if (insuranceInput.trim()) {
      onStartChat("general", "내 보험사 입력", `내 보험사는 ${insuranceInput} 입니다.`)
      onClose()
      setInsuranceInput("")
      setSelectedCompanies([])
    } else if (selectedCompanies.length > 0) {
      onComplete(selectedCompanies)
      onClose()
      setSelectedCompanies([])
    }
  }

  const handleNoInsurance = () => {
    onComplete(null)
    onClose()
    setSelectedCompanies([])
    setInsuranceInput("")
    onStartChat("general", "신규 보험 가입 문의", "저는 보험이 없어요, 신규로 가입하고 싶어요.")
  }

  const handleClose = () => {
    onClose()
    setInsuranceInput("")
    setSearchTerm("")
  }

  const filteredCompanies = (category: string) => {
    const companies = INSURANCE_COMPANIES_CATEGORIZED[category as keyof typeof INSURANCE_COMPANIES_CATEGORIZED] || [];
    return companies.filter(company =>
      company.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-base font-normal">나의 보험 (아래 셋중에 하나만 선택해서 입력 해주세요)</DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-4 p-2">
          {/* 내 보험사 입력하기 채팅창 - 최상단 */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">내 보험사 입력하기</h4>
            <Input
              placeholder="예: 삼성생명, 현대해상"
              value={insuranceInput}
              onChange={(e) => setInsuranceInput(e.target.value)}
              className="w-full"
            />
          </div>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <Separator />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">또는</span>
            </div>
          </div>

          {/* 보험 없음 옵션 */}
          <Button
            variant="outline"
            className="w-full text-left justify-center h-auto p-3 text-orange-600 border-orange-300 hover:bg-orange-50"
            onClick={handleNoInsurance}
          >
            저는 보험이 없어요, 신규로 가입하고 싶어요
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <Separator />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-gray-500">또는</span>
            </div>
          </div>

          {/* 보험사 검색 및 선택 */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-700">보험사 선택하기</h4>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="보험사 검색"
                className="pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <ScrollArea className="h-64 border rounded-md p-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4"> {/* Grid for categories */}
                {Object.keys(INSURANCE_COMPANIES_CATEGORIZED).map((category) => (
                  <div key={category} className="flex flex-col"> {/* Each category column */}
                    <h5 className="font-semibold text-gray-800 mb-2 whitespace-nowrap">{category}</h5>
                    <div className="flex flex-col gap-2"> {/* Vertical companies within category */}
                      {filteredCompanies(category).map((company) => (
                        <Card
                          key={company}
                          className={`cursor-pointer transition-all duration-200 ${
                            selectedCompanies.includes(company)
                              ? "ring-2 ring-yellow-400 shadow-lg bg-yellow-50"
                              : "bg-white hover:bg-gray-50"
                          }`}
                          onClick={() => handleToggleCompany(company)}
                        >
                          <CardContent className="flex items-center justify-between p-3">
                            <div className="flex items-center space-x-2">
                              <span className="text-xl">{INSURANCE_COMPANY_ICONS[company] || "🏢"}</span>
                              <p className="text-sm font-medium">{company}</p>
                            </div>
                            {selectedCompanies.includes(company) && (
                              <Check className="h-4 w-4 text-yellow-600" />
                            )}
                          </CardContent>
                        </Card>
                      ))}
                      {filteredCompanies(category).length === 0 && searchTerm && (
                        <p className="text-center text-xs text-gray-500 py-2">검색 결과 없음</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {Object.keys(INSURANCE_COMPANIES_CATEGORIZED).every(category => filteredCompanies(category).length === 0) && !searchTerm && (
                <p className="text-center text-sm text-gray-500 py-4">선택할 보험사가 없습니다.</p>
              )}
            </ScrollArea>
            <p className="text-xs text-gray-500 mt-2">
              * 실제 로고는 직접 교체해주세요.
            </p>
          </div>
        </div>

        {/* 완료 버튼 */}
        <div className="flex justify-end p-4 border-t">
          <Button
            onClick={handleComplete}
            disabled={!insuranceInput.trim() && selectedCompanies.length === 0}
            className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
          >
            완료
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
